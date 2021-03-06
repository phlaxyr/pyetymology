import json
import warnings
from enum import Enum
from typing import Optional

import requests
from requests import Response

from pyetymology.eobjects.mwparserhelper import wikitextparse, reduce_to_one_lang
# from pyetymology.eobjects.wikikey import WikiKey
from pyetymology.etyobjects import MissingException
from pyetymology.langhelper import Language

session = requests.Session()
session.mount("http://", requests.adapters.HTTPAdapter(max_retries=2))  # retry up to 2 times
session.mount("https://", requests.adapters.HTTPAdapter(max_retries=2))

class APIResult:
    def __init__(self, fullurl, response:Optional[Response]=None, jsn:Optional[Response]=None):
        if not response or not jsn: # if any is missing
            response, jsn = make_http_request(fullurl)
        self.response = response
        self.jsn = jsn
        self.fullurl = fullurl
        check_json(self)
        self.wikitype = None

    def load_wikitext(self, wkey:Optional['WikiKey'], infer_lang=True, override_lang=False, resolve_multilang=None):
        """
        Setting infer_lang=True enables Lang Inferral
        This means after this, Lang should be defined always, or an error thrown
        """
        jsoninfo = parse_json(self, wkey) # a lot of code here

        """
        # TODO: more graceful failure method. For example on failure, use a lambda to pick a language
                    if resolve_multilang:
                        resolve_multilang(wkey)
                    else:
                        raise ValueError(f'fullurl {fullurl} does not designate a language!') # default implementation of resolve_multilang is to throw an error
                        """
        if jsoninfo[0] == "parse":
            self.wikitype, self.wikitext, self.wikiresponse, self.dom, self.Lang = jsoninfo
            if wkey.Lang and wkey.Lang.langqstr != self.Lang.langqstr: # Something's being overriden, which is bad
                warnings.warn(f"Langname is being switched and overridden from {wkey.Lang.langname} to {self.Lang.langname} for word {wkey.word}! They should be the same!")
            if infer_lang:
                if not wkey.Lang:
                    wkey.Lang = self.Lang
            if override_lang:
                wkey.Lang = self.Lang
                # if Lang is something else, then we switched langs altogether. This is really weird
        elif jsoninfo[0] == "query":
            self.wikitype, self.derivs = jsoninfo
    @property
    def text(self):
        return self.response.text
    @property
    def langname(self):
        return self.Lang.langname
def make_http_request(fullurl: str, online=True):
    if online:
        global session
        res = session.get(fullurl)
        #cache res TODO: implement better caching with test_'s fetch stuff
    else:
        raise Exception("offline browsing not implemented yet")
    txt = res.text
    # print(txt)
    jsn = json.loads(txt) #type: json
    return res, jsn
def check_json(result: APIResult):
    jsn = result.jsn
    fullurl = result.fullurl
    if "error" in jsn:
        if "info" in jsn["error"]:
            if jsn["error"]["info"] == "The page you specified doesn't exist.":
                raise MissingException(f"No page found for specified url {fullurl}.", missing_thing="page")
            else:
                raise ValueError(f"Unexpected error info {jsn['error']['info']} for url {result.fullurl}")
        raise MissingException(
            f"Unexpected error, info not found. Url: {fullurl} JSON: {str(jsn['error'])}",
            missing_thing="everything")
def parse_json(result: APIResult, wkey: Optional['WikiKey'] = None, use_lang=None, resolve_multilang=None):
    """
    BUILT IN: Lang reducing function.
    AFTER parse_json, lang should be defined ALWAYS, or an error thrown.
    """
    jsn = result.jsn

    # the above will have thrown an error
    # if result.deriv:
    if "query" in jsn:
        # assert deriv NAH we don't need to assert
        assert wkey.deriv
        derivs = [pair["title"] for pair in result.jsn["query"]["categorymembers"]]
        return "query", derivs
        # origin = Originator(me, o_id=query_id)
        # return DummyQuery(me=me, origin=origin, child_queries=derivs, with_lang=Language(langcode="en"))

    # https://en.wiktionary.org/w/api.php?action=query&list=categorymembers&cmtitle=Category:English_terms_derived_from_the_Proto-Indo-European_root_*ple%E1%B8%B1-&cmprop=title
    elif "parse" in jsn:
        wikitext = jsn["parse"]["wikitext"]
        res, dom = wikitextparse(wikitext, redundance=False)
        # Here was the lang detection
        dom, langname = reduce_to_one_lang(dom, use_lang=use_lang if use_lang else wkey.Lang.langname)

        title = jsn["parse"]["title"]
        if title.startswith("Reconstruction:"):
            # we have a reconstr on our hands
            Lang = Language(langname=langname, is_reconstr=True)
        else:
            Lang = Language(langname=langname)
        return "parse", wikitext, res, dom, Lang
    else:
        raise Exception(f"JSON malformed; top-level not found! (neither parse, query, nor error found) JSON: {jsn} URL: {result.fullurl}")


