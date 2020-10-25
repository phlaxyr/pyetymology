import grandalf
import mwparserfromhell as mwp
from pyetymology import helper_api as helper
import networkx as nx
import pyetymology.langcode as langcode
import matplotlib.pyplot as plt
def ety_parse_routine(wikitext, me, word, lang, def_id):
    res = mwp.parse(wikitext)
    # res = wtp.parse(wikitext)

    dom = res.get_sections()
    # print(pprint(dom))
    dom = helper.get_by_lang(dom, lang)

    _exhausted = object()
    if not dom or next(dom, _exhausted) == _exhausted:
        raise Exception(f"Word \"{word}\" has no entry under language {lang}")

    ety_flag = False
    sections = helper.get_by_level(dom, 3)

    for sec in sections:

        """
        if sec[0].startswith("===Verb==="):
            for subsec in helper.get_by_level(sec, 4):
                pass# print("-"+repr(subsec))
        el"""
        if sec[0].startswith("===Etymology") and not sec[0].startswith("===Etymology==="):
            # Therefore, if it starts with something like ===Etymology 1===
            if def_id is None:
                def_id = input("Multiple definitions detected. Enter an ID: ")
        if sec[0].startswith("===Etymology===") or sec[0].startswith(f"===Etymology {def_id}"):
            if not ety_flag:
                ety_flag = True
            else:
                raise Exception("Etymology is being parsed twice? ")
            # for node in sec[0].ifilter_templates(): #type: mwp.wikicode.Template
            #     sec[0].remove(node)

            dotyet = False
            firstsentence = []
            for node in sec[0].ifilter(recursive=False):  # type: mwp.wikicode.Node
                # .filter_templates(): #type: mwp.wikicode.Template
                # if etytemp

                if isinstance(node, mwp.wikicode.Template):
                    etyr = helper.EtyRelation(node)
                    # print(str(etyr))
                    if not dotyet:
                        firstsentence.append(etyr)

                else:
                    # print(str(node))
                    if not dotyet:  # if we're in the first sentence
                        if ("." in node):  # if we reach the end
                            firstsentence.append(
                                node[:node.index(".") + 1])  # get everything up to, and including, the period
                            dotyet = True
                        else:
                            firstsentence.append(
                                node)  # if we haven't reached the period, we're in the middle. capture that node

            print("1st " + repr(firstsentence))
            ancestry = []

            G = nx.DiGraph()
            prev = me
            G.add_node(me, pos=(0, 0))

            between_text = []

            check_type = False
            cache = langcode.cache.Cache(4)
            for bib in firstsentence:  # time to analyze the immediate etymology ("ancestry")
                if bib is None:
                    continue
                if isinstance(bib, helper.EtyRelation):
                    bib: helper.EtyRelation
                    cache.put(bib)

                    if any(helper.is_in(bib.rtype, x) for x in
                           (helper.EtyRelation.ety_abbrs, helper.EtyRelation.aff_abbrs, helper.EtyRelation.sim_abbrs)):
                        # inh, der, bor, m
                        # print(between_text)
                        if any("+" in s for s in
                               between_text):  # or helper_api.is_in(bib.rtype, helper_api.EtyRelation.aff_abbrs):
                            prevs_parents = G.edges(nbunch=prev)  #
                            # prev2 = cache.nth_prev(2)
                            # print("parnt: " + str(parnt))
                            parnt = next(iter(prevs_parents), (None, None))[1]
                            # parnt = prev2
                            G.add_node(bib)
                            G.add_edge(bib, parnt)
                            # print(cache.array)

                            # sister node
                        else:
                            G.add_node(bib)
                            if prev:
                                G.add_edge(bib, prev)
                        prev = bib
                    else:
                        print(bib)
                    between_text = []
                else:
                    between_text.append(bib)

            print("...drawing graph...")
            # print(G.size())
            pos = nx.get_node_attributes(G, 'pos')
            g = grandalf.utils.convert_nextworkx_graph_to_grandalf(G)
            from grandalf.layouts import SugiyamaLayout
            class defaultview(object):
                w, h = 10, 10

            for v in g.V(): v.view = defaultview()
            sug = SugiyamaLayout(g.C[0])
            sug.init_all()  # roots=[V[0]]) #, inverted_edges=[V[4].e_to(V[0])])
            sug.draw()
            poses = {v.data: (-v.view.xy[0], -v.view.xy[1]) for v in g.C[0].sV}
            nx.draw(G, pos=poses, with_labels=True)
            plt.show()

        else:
            pass  # print(repr(sec))
    if not ety_flag:
        raise Exception("Etymology not detected. (If a word has multiple definitions, you must specify it.)")