#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
#  Copyright 2015 Pascual Martinez-Gomez
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import unittest

from lxml import etree

from ccg2lambda_tools import assign_semantics_to_ccg
from logic_parser import lexpr
from semantic_index import SemanticIndex
from semantic_index import SemanticRule
from semantic_types import build_dynamic_library
from semantic_types import build_library_entry
from semantic_types import combine_signatures_or_rename_preds
from semantic_types import convert_coq_signatures_to_nltk
from semantic_types import convert_coq_to_nltk_type
from semantic_types import get_coq_types
from semantic_types import merge_dynamic_libraries
from semantic_types import read_type
from semantic_types import resolve_types

from nltk.sem.logic import Variable, Expression

class combine_signatures_or_rename_predsTestCase(unittest.TestCase):
    # def test_resolve(self):
    #     expr = lexpr(r'pred1(x)')
    #     from pudb import set_trace; set_trace()
    #     resolve_types(expr)
    #     expr2 = lexpr(r'pred1(x) & pred2(e) & pred3(v)')
    #     expr3 = lexpr(r'exists x e. (pred1(x) & pred2(e) & (exists x. pred2(x)))')
    #     # print(expr2.visit_structured(
    #     #     lambda e: e,
    #     #     lambda es: [e.replace(Variable('pred2'), lexpr('pred22')) for e in es]))
    #     print(expr2.visit_structured(
    #         lambda e: e.replace(Variable('pred2'), lexpr('pred22')),
    #         expr2.__class__))

    def test_different_onepred(self):
        exprs = [lexpr(r'pred1(x)'), lexpr(r'pred2(x)')]
        sigs = [resolve_types(e) for e in exprs]
        sig, exprs_new = combine_signatures_or_rename_preds(sigs, exprs)
        self.assertEqual(3, len(sig), msg='Unexpected signature: {0}'.format(sig))
        self.assertEqual(exprs, exprs_new)

    def test_equal_onepred(self):
        exprs = [lexpr(r'pred1(x)'), lexpr(r'pred1(x)')]
        sigs = [resolve_types(e) for e in exprs]
        sig, exprs_new = combine_signatures_or_rename_preds(sigs, exprs)
        self.assertEqual(2, len(sig), msg='Unexpected signature: {0}'.format(sig))
        self.assertEqual(exprs, exprs_new)

    def test_equalvar_onepred(self):
        exprs = [lexpr(r'pred1(x)'), lexpr(r'pred1(y)')]
        sigs = [resolve_types(e) for e in exprs]
        sig, exprs_new = combine_signatures_or_rename_preds(sigs, exprs)
        self.assertEqual(3, len(sig), msg='Unexpected signature: {0}'.format(sig))
        self.assertEqual(exprs, exprs_new)

    def test_different_one_two_pred(self):
        exprs = [lexpr(r'pred1(x)'), lexpr(r'pred1(x,y)')]
        expected_exprs = [lexpr(r'pred1_en(x)'), lexpr(r'pred1_2(x,y)')]
        sigs = [resolve_types(e) for e in exprs]
        sig, exprs_new = combine_signatures_or_rename_preds(sigs, exprs)
        self.assertEqual(4, len(sig), msg='Unexpected signature: {0}'.format(sig))
        self.assertEqual(exprs[0], exprs_new[0])
        self.assertNotEqual(exprs[1], exprs_new[1])

    def test_different_one_pred_vartype(self):
        exprs = [lexpr(r'pred1(x)'), lexpr(r'pred1(F)')]
        expected_exprs = [lexpr(r'pred1_en(x)'), lexpr(r'pred1_pr(F)')]
        # sigs = [resolve_types(e) for e in exprs]
        # from pudb import set_trace; set_trace()
        sig, exprs_new = combine_signatures_or_rename_preds(3, exprs)
        self.assertEqual(4, len(sig), msg='Unexpected signature: {0}'.format(sig))
        self.assertEqual(expected_exprs, exprs)
        self.assertEqual(exprs[0], exprs_new[0])
        self.assertNotEqual(exprs[1], exprs_new[1])
        # print(sig)
        # print(exprs_new)

    def test_different_in_same_expression(self):
        # exprs = [lexpr(r'pred1(x) & pred1(F)'), lexpr(r'pred1(F)')]
        # exprs = [lexpr(r'pred1(e) & pred1(x)'), lexpr(r'pred1(e)')]
        expr = lexpr(r'pred1(e) & pred1(x)')
        # from pudb import set_trace; set_trace()
        from semantic_types import resolve_types_and_rename_collisions
        sigs, new_expr = resolve_types_and_rename_collisions(expr)
        # sig, exprs_new = combine_signatures_or_rename_preds(sigs, exprs)
        # print(sig)
        # print(exprs_new)
        # expected_exprs_new = [
        #     lexpr(r'pred1_ev(v) & pred1_en(x)'), lexpr(r'pred1_ev(v)')]
        expected_expr = lexpr(r'pred1_v(e) & pred1_e(x)')
        self.assertEqual(expected_expr, new_expr)
        # self.assertEqual(4, len(sig), msg='Unexpected signature: {0}'.format(sig))
        # self.assertEqual(exprs[0], exprs_new[0])
        # self.assertNotEqual(exprs[1], exprs_new[1])

    # def test_different_in_same_expression(self):
    #     # exprs = [lexpr(r'pred1(x) & pred1(F)'), lexpr(r'pred1(F)')]
    #     # exprs = [lexpr(r'pred1(e) & pred1(x)'), lexpr(r'pred1(e)')]
    #     exprs = [lexpr(r'pred1(e) & pred1(x)')]
    #     # from pudb import set_trace; set_trace()
    #     sigs = [resolve_types(e) for e in exprs]
    #     # sig, exprs_new = combine_signatures_or_rename_preds(sigs, exprs)
    #     # print(sig)
    #     # print(exprs_new)
    #     # expected_exprs_new = [
    #     #     lexpr(r'pred1_ev(v) & pred1_en(x)'), lexpr(r'pred1_ev(v)')]
    #     expected_exprs_new = [lexpr(r'pred1_v(e) & pred1_e(x)')]
    #     self.assertEqual(expected_exprs_new, exprs_new)
    #     self.assertEqual(4, len(sig), msg='Unexpected signature: {0}'.format(sig))
    #     self.assertEqual(exprs[0], exprs_new[0])
    #     self.assertNotEqual(exprs[1], exprs_new[1])

# TODO: also test for types that are Propositions 't'.

def nltk_sig_to_coq_lib(nltk_sig):
   # Convert into coq style library entries.
    coq_lib = []
    for predicate, pred_type in nltk_sig.items():
        library_entry = build_library_entry(predicate, pred_type)
        coq_lib.append(library_entry)
    return sorted(set(coq_lib))

class build_arbitrary_dynamic_libraryTestCase(unittest.TestCase):
    def test_lexical_unary_one_type(self):
        semantic_index = SemanticIndex(None)
        semantic_rules = [SemanticRule(r'N', r'\P.P', {'coq_type' : 'Entity -> Prop'}),
                          SemanticRule(r'NP', r'\P.(P -> P)', {'rule' : 'lex'})]
        semantic_index.rules = semantic_rules
        sentence_str = r"""
      <sentence id="s1">
        <tokens>
          <token base="base1" pos="pos1" surf="surf1" id="t1_1"/>
        </tokens>
        <ccg root="sp1-2">
          <span terminal="t1_1" category="N" end="2" begin="1" id="sp1-1"/>
          <span child="sp1-1" rule="lex" category="NP" end="2" begin="1" id="sp1-2"/>
        </ccg>
      </sentence>
    """
        sentence = etree.fromstring(sentence_str)
        ccg_tree = assign_semantics_to_ccg(sentence, semantic_index)
        coq_types = get_coq_types(ccg_tree)
        expected_coq_types = ["Parameter _base1 : Entity -> Prop."]
        self.assertEqual(expected_coq_types, coq_types)

    def test_lexical_binary_two_types(self):
        semantic_index = SemanticIndex(None)
        semantic_rules = [SemanticRule(r'cat1', r'\P.P', {'coq_type' : 'Entity -> Prop'}),
                          SemanticRule(r'cat2', r'\P.P', {'coq_type' : 'Entity -> Prop -> Prop'}),
                          SemanticRule(r'NP', r'\P Q.(Q -> P)', {'rule' : 'lex'})]
        semantic_index.rules = semantic_rules
        sentence_str = r"""
      <sentence id="s1">
        <tokens>
          <token base="base1" pos="pos1" surf="surf1" id="t1_1"/>
          <token base="base2" pos="pos2" surf="surf2" id="t1_2"/>
        </tokens>
        <ccg root="sp1-3">
          <span terminal="t1_1" category="cat1" end="2" begin="1" id="sp1-1"/>
          <span terminal="t1_2" category="cat2" end="3" begin="2" id="sp1-2"/>
          <span child="sp1-1 sp1-2" rule="lex" category="NP" end="3" begin="1" id="sp1-3"/>
        </ccg>
      </sentence>
    """
        sentence = etree.fromstring(sentence_str)
        ccg_tree = assign_semantics_to_ccg(sentence, semantic_index)
        coq_types = get_coq_types(ccg_tree)
        expected_coq_types = ["Parameter _base1 : Entity -> Prop.",
                              "Parameter _base2 : Entity -> Prop -> Prop."]
        self.assertEqual(expected_coq_types, coq_types)

    def test_lexical_binary_one_type(self):
        semantic_index = SemanticIndex(None)
        semantic_rules = [SemanticRule(r'cat1', r'\P.P'),
                          SemanticRule(r'cat2', r'\Q x.Q(x)', {'coq_type' : 'Entity -> Prop'}),
                          SemanticRule(r'NP', r'\P Q x.(P -> Q(x))', {'rule' : 'lex'})]
        semantic_index.rules = semantic_rules
        sentence_str = r"""
      <sentence id="s1">
        <tokens>
          <token base="base1" pos="pos1" surf="surf1" id="t1_1"/>
          <token base="base2" pos="pos2" surf="surf2" id="t1_2"/>
        </tokens>
        <ccg root="sp1-3">
          <span terminal="t1_1" category="cat1" end="2" begin="1" id="sp1-1"/>
          <span terminal="t1_2" category="cat2" end="3" begin="2" id="sp1-2"/>
          <span child="sp1-1 sp1-2" rule="lex" category="NP" end="3" begin="1" id="sp1-3"/>
        </ccg>
      </sentence>
    """
        sentence = etree.fromstring(sentence_str)
        ccg_tree = assign_semantics_to_ccg(sentence, semantic_index)
        coq_types = get_coq_types(ccg_tree)
        expected_coq_types = ["Parameter _base2 : Entity -> Prop."]
        self.assertEqual(expected_coq_types, coq_types)

class ArbiAutoTypesTestCase(unittest.TestCase):
    def test_lexical_binary_one_type(self):
        semantic_index = SemanticIndex(None)
        semantic_rules = [SemanticRule(r'cat1', r'\P x.P(x)'),
                          SemanticRule(r'cat2', r'\P x.P(x)', {'coq_type' : 'Entity -> Prop'}),
                          SemanticRule(r'NP', r'\P Q x.(Q(x) -> P(x))', {'rule' : 'lex'})]
        semantic_index.rules = semantic_rules
        sentence_str = r"""
      <sentence id="s1">
        <tokens>
          <token base="base1" pos="pos1" surf="surf1" id="t1_1"/>
          <token base="base2" pos="pos2" surf="surf2" id="t1_2"/>
        </tokens>
        <ccg root="sp1-3">
          <span terminal="t1_1" category="cat1" end="2" begin="1" id="sp1-1"/>
          <span terminal="t1_2" category="cat2" end="3" begin="2" id="sp1-2"/>
          <span child="sp1-1 sp1-2" rule="lex" category="NP" end="3" begin="1" id="sp1-3"/>
        </ccg>
      </sentence>
    """
        sentence = etree.fromstring(sentence_str)
        ccg_tree = assign_semantics_to_ccg(sentence, semantic_index)
        coq_lib = get_coq_types(ccg_tree)
        expected_coq_lib = ["Parameter _base2 : Entity -> Prop."]
        self.assertEqual(expected_coq_lib, coq_lib)
        expression = [ccg_tree.get('sem')]
        coq_sig = convert_coq_signatures_to_nltk(coq_lib)
        nltk_lib, _ = build_dynamic_library(expression, coq_sig)
        lib = merge_dynamic_libraries(coq_sig, nltk_lib, './coqlib.v', sentence)
        expected_lib = ["Parameter _base2 : Entity -> Prop.",
                        "Parameter _base1 : Entity -> Prop."]
        self.assertCountEqual(expected_lib, lib)

    def test_lexical_binary_no_type(self):
        semantic_index = SemanticIndex(None)
        semantic_rules = [SemanticRule(r'cat1', r'\P x.P(x)'),
                          SemanticRule(r'cat2', r'\P x.P(x)'),
                          SemanticRule(r'NP', r'\P Q x.(Q(x) -> P(x))', {'rule' : 'lex'})]
        semantic_index.rules = semantic_rules
        sentence_str = r"""
      <sentence id="s1">
        <tokens>
          <token base="base1" pos="pos1" surf="surf1" id="t1_1"/>
          <token base="base2" pos="pos2" surf="surf2" id="t1_2"/>
        </tokens>
        <ccg root="sp1-3">
          <span terminal="t1_1" category="cat1" end="2" begin="1" id="sp1-1"/>
          <span terminal="t1_2" category="cat2" end="3" begin="2" id="sp1-2"/>
          <span child="sp1-1 sp1-2" rule="lex" category="NP" end="3" begin="1" id="sp1-3"/>
        </ccg>
      </sentence>
    """
        sentence = etree.fromstring(sentence_str)
        ccg_tree = assign_semantics_to_ccg(sentence, semantic_index)
        coq_lib = get_coq_types(ccg_tree)
        expected_coq_lib = []
        self.assertEqual(expected_coq_lib, coq_lib)
        expression = [ccg_tree.get('sem')]
        coq_sig = convert_coq_signatures_to_nltk(coq_lib)
        nltk_lib, _ = build_dynamic_library(expression, coq_sig)
        lib = merge_dynamic_libraries(coq_lib, nltk_lib, './coqlib.v', sentence)
        expected_lib = ["Parameter _base2 : Entity -> Prop.",
                        "Parameter _base1 : Entity -> Prop."]
        self.assertCountEqual(expected_lib, lib)

    def test_lexical_binary_one_nltk_complex_type(self):
        semantic_index = SemanticIndex(None)
        semantic_rules = [SemanticRule(r'cat1', r'\P x.P(x)'),
                          SemanticRule(r'cat2', r'\Q x y.Q(x, y)'),
                          SemanticRule(r'NP', r'\P Q x y.(P(x) -> Q(x, y))', {'rule' : 'lex'})]
        semantic_index.rules = semantic_rules
        sentence_str = r"""
      <sentence id="s1">
        <tokens>
          <token base="base1" pos="pos1" surf="surf1" id="t1_1"/>
          <token base="base2" pos="pos2" surf="surf2" id="t1_2"/>
        </tokens>
        <ccg root="sp1-3">
          <span terminal="t1_1" category="cat1" end="2" begin="1" id="sp1-1"/>
          <span terminal="t1_2" category="cat2" end="3" begin="2" id="sp1-2"/>
          <span child="sp1-1 sp1-2" rule="lex" category="NP" end="3" begin="1" id="sp1-3"/>
        </ccg>
      </sentence>
    """
        sentence = etree.fromstring(sentence_str)
        ccg_tree = assign_semantics_to_ccg(sentence, semantic_index)
        coq_lib = get_coq_types(ccg_tree)
        expected_coq_lib = []
        self.assertEqual(expected_coq_lib, coq_lib)
        expression = [ccg_tree.get('sem')]
        coq_sig = convert_coq_signatures_to_nltk(coq_lib)
        nltk_lib, _ = build_dynamic_library(expression, coq_sig)
        lib = merge_dynamic_libraries(coq_lib, nltk_lib, './coqlib.v', sentence)
        expected_lib = ["Parameter _base2 : Entity -> (Entity -> Prop).",
                        "Parameter _base1 : Entity -> Prop."]
        self.assertCountEqual(expected_lib, lib)

    def test_lexical_binary_one_coq_complex_type(self):
        semantic_index = SemanticIndex(None)
        semantic_rules = [SemanticRule(r'cat1', r'\P x.P(x)'),
                          SemanticRule(r'cat2', r'\Q R S.Q(R, S)', {'coq_type' : 'Prop -> Entity -> Prop'}),
                          SemanticRule(r'NP', r'\P Q x R S.(P(x) -> Q(R, S))', {'rule' : 'lex'})]
        semantic_index.rules = semantic_rules
        sentence_str = r"""
      <sentence id="s1">
        <tokens>
          <token base="base1" pos="pos1" surf="surf1" id="t1_1"/>
          <token base="base2" pos="pos2" surf="surf2" id="t1_2"/>
        </tokens>
        <ccg root="sp1-3">
          <span terminal="t1_1" category="cat1" end="2" begin="1" id="sp1-1"/>
          <span terminal="t1_2" category="cat2" end="3" begin="2" id="sp1-2"/>
          <span child="sp1-1 sp1-2" rule="lex" category="NP" end="3" begin="1" id="sp1-3"/>
        </ccg>
      </sentence>
    """
        sentence = etree.fromstring(sentence_str)
        ccg_tree = assign_semantics_to_ccg(sentence, semantic_index)
        coq_lib = get_coq_types(ccg_tree)
        expected_coq_lib = ['Parameter _base2 : Prop -> Entity -> Prop.']
        self.assertEqual(expected_coq_lib, coq_lib)
        expression = [ccg_tree.get('sem')]
        coq_sig = convert_coq_signatures_to_nltk(coq_lib)
        nltk_lib, _ = build_dynamic_library(expression, coq_sig)
        lib = merge_dynamic_libraries(coq_sig, nltk_lib, './coqlib.v', sentence)
        expected_lib = ["Parameter _base2 : Prop -> (Entity -> Prop).",
                        "Parameter _base1 : Entity -> Prop."]
        self.assertCountEqual(expected_lib, lib)

    def test_lexical_binary_two_coq_complex_type(self):
        semantic_index = SemanticIndex(None)
        semantic_rules = [SemanticRule(r'cat1', r'\P x R.P(x, R)', {'coq_type' : 'Entity -> Prop -> Prop'}),
                          SemanticRule(r'cat2', r'\Q S T.Q(S, T)', {'coq_type' : 'Prop -> Entity -> Prop'}),
                          SemanticRule(r'NP', r'\P Q x R S T.(Q(x, R) -> P(S, T))', {'rule' : 'lex'})]
        semantic_index.rules = semantic_rules
        sentence_str = r"""
      <sentence id="s1">
        <tokens>
          <token base="base1" pos="pos1" surf="surf1" id="t1_1"/>
          <token base="base2" pos="pos2" surf="surf2" id="t1_2"/>
        </tokens>
        <ccg root="sp1-3">
          <span terminal="t1_1" category="cat1" end="2" begin="1" id="sp1-1"/>
          <span terminal="t1_2" category="cat2" end="3" begin="2" id="sp1-2"/>
          <span child="sp1-1 sp1-2" rule="lex" category="NP" end="3" begin="1" id="sp1-3"/>
        </ccg>
      </sentence>
    """
        sentence = etree.fromstring(sentence_str)
        ccg_tree = assign_semantics_to_ccg(sentence, semantic_index)
        coq_lib = get_coq_types(ccg_tree)
        expected_coq_lib = ['Parameter _base1 : Entity -> Prop -> Prop.',
                            'Parameter _base2 : Prop -> Entity -> Prop.']
        self.assertEqual(expected_coq_lib, coq_lib)
        expression = [ccg_tree.get('sem')]
        coq_sig = convert_coq_signatures_to_nltk(coq_lib)
        nltk_lib, _ = build_dynamic_library(expression, coq_sig)
        lib = merge_dynamic_libraries(coq_sig, nltk_lib, './coqlib.v', sentence)
        expected_lib = ["Parameter _base2 : Prop -> (Entity -> Prop).",
                        "Parameter _base1 : Entity -> (Prop -> Prop)."]
        self.assertCountEqual(expected_lib, lib)

class Coq2NLTKSignaturesTestCase(unittest.TestCase):
    def test_entity(self):
        coq_sig = ['Parameter base1 : Entity.',
                   'Parameter base2 : Prop.']
        nltk_sig = convert_coq_signatures_to_nltk(coq_sig)
        expected_nltk_sig = {'base1' : read_type('e'),
                             'base2' : read_type('t')}
        self.assertEqual(expected_nltk_sig, nltk_sig)

class Coq2NLTKTypesTestCase(unittest.TestCase):
    def test_entity(self):
        coq_type = 'Parameter base : Entity.'
        nltk_type = convert_coq_to_nltk_type(coq_type)
        expected_nltk_type = {'base' : read_type('e')}
        self.assertEqual(expected_nltk_type, nltk_type)

    def test_property(self):
        coq_type = 'Parameter base : Prop.'
        nltk_type = convert_coq_to_nltk_type(coq_type)
        expected_nltk_type = {'base' : read_type('t')}
        self.assertEqual(expected_nltk_type, nltk_type)

    def test_event(self):
        coq_type = 'Parameter base : Event.'
        nltk_type = convert_coq_to_nltk_type(coq_type)
        expected_nltk_type = {'base' : read_type('v')}
        self.assertEqual(expected_nltk_type, nltk_type)

    def test_wrong_type(self):
        coq_type = 'Parameter base : YYY.'
        self.assertRaises(ValueError, convert_coq_to_nltk_type, coq_type)

    def test_entity_property(self):
        coq_type = 'Parameter base : Entity -> Prop.'
        nltk_type = convert_coq_to_nltk_type(coq_type)
        expected_nltk_type = {'base' : read_type('<e,t>')}
        self.assertEqual(expected_nltk_type, nltk_type)

    def test_entity_entity_property(self):
        coq_type = 'Parameter base : Entity -> Entity -> Prop.'
        nltk_type = convert_coq_to_nltk_type(coq_type)
        expected_nltk_type = {'base' : read_type('<e,<e,t>>')}
        self.assertEqual(expected_nltk_type, nltk_type)

    def test_entity_property_property(self):
        coq_type = 'Parameter base : Entity -> Prop -> Prop.'
        nltk_type = convert_coq_to_nltk_type(coq_type)
        expected_nltk_type = {'base' : read_type('<e,<t,t>>')}
        self.assertEqual(expected_nltk_type, nltk_type)

    def test_entity_property_and_property(self):
        coq_type = 'Parameter base : (Entity -> Prop) -> Prop.'
        nltk_type = convert_coq_to_nltk_type(coq_type)
        expected_nltk_type = {'base' : read_type('<<e,t>,t>>')}
        self.assertEqual(expected_nltk_type, nltk_type)

    def test_entity_property_and_property_entity(self):
        coq_type = 'Parameter base : (Entity -> Prop) -> (Prop -> Entity).'
        nltk_type = convert_coq_to_nltk_type(coq_type)
        expected_nltk_type = {'base' : read_type('<<e,t>,<t,e>>')}
        self.assertEqual(expected_nltk_type, nltk_type)

    def test_event_and_entity_property(self):
        coq_type = 'Parameter base : Event -> (Entity -> Prop).'
        nltk_type = convert_coq_to_nltk_type(coq_type)
        expected_nltk_type = {'base' : read_type('<v,<e,t>>')}
        self.assertEqual(expected_nltk_type, nltk_type)

class build_dynamic_libraryTestCase(unittest.TestCase):
    def test_entity(self):
        exprs = [lexpr('Python')]
        dynamic_library, _ = build_dynamic_library(exprs)
        dynamic_library = nltk_sig_to_coq_lib(dynamic_library)
        expected_dynamic_library = \
          ['Parameter Python : Entity.']
        self.assertEqual(expected_dynamic_library, dynamic_library)

    def test_predicate1_argument1(self):
        exprs = [lexpr('language(Python)')]
        dynamic_library, _ = build_dynamic_library(exprs)
        dynamic_library = nltk_sig_to_coq_lib(dynamic_library)
        expected_dynamic_library = \
          ['Parameter Python : Entity.',
           'Parameter language : Entity -> Prop.']
        for item in dynamic_library:
            self.assertIn(item, expected_dynamic_library)
        self.assertEqual(len(expected_dynamic_library), len(dynamic_library))

    def test_predicate1_argument2(self):
        exprs = [lexpr('language(Python, Scala)')]
        dynamic_library, _ = build_dynamic_library(exprs)
        dynamic_library = nltk_sig_to_coq_lib(dynamic_library)
        expected_dynamic_library = \
          ['Parameter Python : Entity.',
           'Parameter Scala : Entity.',
           'Parameter language : Entity -> (Entity -> Prop).']
        for item in dynamic_library:
            self.assertIn(item, expected_dynamic_library)
        self.assertEqual(len(expected_dynamic_library), len(dynamic_library))

    def test_predicate2_argument1_and_2(self):
        exprs = [lexpr('AND(language(Python, Scala), nice(Python))')]
        dynamic_library, _ = build_dynamic_library(exprs)
        dynamic_library = nltk_sig_to_coq_lib(dynamic_library)
        expected_dynamic_library = \
          ['Parameter nice : Entity -> Prop.',
           'Parameter Python : Entity.',
           'Parameter Scala : Entity.',
           'Parameter language : Entity -> (Entity -> Prop).']
        for item in dynamic_library:
            self.assertIn(item, expected_dynamic_library)
        self.assertEqual(len(expected_dynamic_library), len(dynamic_library))

    def test_predicate2_argument1_and_2Exprs2(self):
        exprs = [lexpr('language(Python, Scala)'), lexpr('nice(Python)')]
        dynamic_library, _ = build_dynamic_library(exprs)
        dynamic_library = nltk_sig_to_coq_lib(dynamic_library)
        expected_dynamic_library = \
          ['Parameter nice : Entity -> Prop.',
           'Parameter Python : Entity.',
           'Parameter Scala : Entity.',
           'Parameter language : Entity -> (Entity -> Prop).']
        for item in dynamic_library:
            self.assertIn(item, expected_dynamic_library)
        self.assertEqual(len(expected_dynamic_library), len(dynamic_library))

    def test_pred1_prop_prop(self):
        exprs = [lexpr('nice(language(Python, Scala))')]
        dynamic_library, _ = build_dynamic_library(exprs)
        dynamic_library = nltk_sig_to_coq_lib(dynamic_library)
        expected_dynamic_library = \
          ['Parameter nice : Prop -> Prop.',
           'Parameter Python : Entity.',
           'Parameter Scala : Entity.',
           'Parameter language : Entity -> (Entity -> Prop).']
        for item in dynamic_library:
            self.assertIn(item, expected_dynamic_library)
        self.assertEqual(len(expected_dynamic_library), len(dynamic_library))

    def test_pred2_prop_prop(self):
        exprs = [lexpr('nice(language(Python, Scala))'),
                 lexpr('fun(language(Python, Scala))')]
        dynamic_library, _ = build_dynamic_library(exprs)
        dynamic_library = nltk_sig_to_coq_lib(dynamic_library)
        expected_dynamic_library = \
          ['Parameter nice : Prop -> Prop.',
           'Parameter fun : Prop -> Prop.',
           'Parameter Python : Entity.',
           'Parameter Scala : Entity.',
           'Parameter language : Entity -> (Entity -> Prop).']
        for item in dynamic_library:
            self.assertIn(item, expected_dynamic_library)
        self.assertEqual(len(expected_dynamic_library), len(dynamic_library))

    def test_exists(self):
        exprs = [lexpr('exists x.P(x)')]
        dynamic_library, _ = build_dynamic_library(exprs)
        dynamic_library = nltk_sig_to_coq_lib(dynamic_library)
        expected_dynamic_library = \
          ['Parameter P : Entity -> Prop.',
           'Parameter x : Entity.']
        for item in dynamic_library:
            self.assertIn(item, expected_dynamic_library)
        self.assertEqual(len(expected_dynamic_library), len(dynamic_library))

    def test_exist(self):
        exprs = [lexpr('exist x.P(x)')]
        dynamic_library, _ = build_dynamic_library(exprs)
        dynamic_library = nltk_sig_to_coq_lib(dynamic_library)
        expected_dynamic_library = \
          ['Parameter P : Entity -> Prop.',
           'Parameter x : Entity.']
        for item in dynamic_library:
            self.assertIn(item, expected_dynamic_library)
        self.assertEqual(len(expected_dynamic_library), len(dynamic_library))

    def test_Lambda1exists1(self):
        exprs = [lexpr('\P.exist x.P(x)')]
        dynamic_library, _ = build_dynamic_library(exprs)
        dynamic_library = nltk_sig_to_coq_lib(dynamic_library)
        expected_dynamic_library = \
          ['Parameter P : Entity -> Prop.',
           'Parameter x : Entity.']
        for item in dynamic_library:
            self.assertIn(item, expected_dynamic_library)
        self.assertEqual(len(expected_dynamic_library), len(dynamic_library))

    def test_Lambda2exists1(self):
        exprs = [lexpr('\P y.exist x.P(x, y)')]
        dynamic_library, _ = build_dynamic_library(exprs)
        dynamic_library = nltk_sig_to_coq_lib(dynamic_library)
        expected_dynamic_library = \
          ['Parameter P : Entity -> (Entity -> Prop).',
           'Parameter x : Entity.',
           'Parameter y : Entity.']
        for item in dynamic_library:
            self.assertIn(item, expected_dynamic_library)
        self.assertEqual(len(expected_dynamic_library), len(dynamic_library))

    def test_Lambda3exists1(self):
        exprs = [lexpr('\P y.\T.exist x.T(P(x, y))')]
        dynamic_library, _ = build_dynamic_library(exprs)
        dynamic_library = nltk_sig_to_coq_lib(dynamic_library)
        expected_dynamic_library = \
          ['Parameter P : Entity -> (Entity -> Prop).',
           'Parameter T : Prop -> Prop.',
           'Parameter x : Entity.',
           'Parameter y : Entity.']
        for item in dynamic_library:
            self.assertIn(item, expected_dynamic_library)
        self.assertEqual(len(expected_dynamic_library), len(dynamic_library))

    def test_Lambda3exists2(self):
        exprs = [lexpr('\P y.\T.exist x.exists z.T(P(x, y), z)')]
        dynamic_library, _ = build_dynamic_library(exprs)
        dynamic_library = nltk_sig_to_coq_lib(dynamic_library)
        expected_dynamic_library = \
          ['Parameter P : Entity -> (Entity -> Prop).',
           'Parameter T : Prop -> (Entity -> Prop).',
           'Parameter x : Entity.',
           'Parameter y : Entity.',
           'Parameter z : Entity.']
        for item in dynamic_library:
            self.assertIn(item, expected_dynamic_library)
        self.assertEqual(len(expected_dynamic_library), len(dynamic_library))

    def test_Lambda3exists2All1(self):
        exprs = [lexpr('\P y.\T.all w.exist x.exists z.T(P(x, y), z, w)')]
        dynamic_library, _ = build_dynamic_library(exprs)
        dynamic_library = nltk_sig_to_coq_lib(dynamic_library)
        expected_dynamic_library = \
          ['Parameter P : Entity -> (Entity -> Prop).',
           'Parameter T : Prop -> (Entity -> (Entity -> Prop)).',
           'Parameter w : Entity.',
           'Parameter x : Entity.',
           'Parameter y : Entity.',
           'Parameter z : Entity.']
        for item in dynamic_library:
            self.assertIn(item, expected_dynamic_library)
        self.assertEqual(len(expected_dynamic_library), len(dynamic_library))

    def test_Lambda3exists2All1Mixed(self):
        exprs = [lexpr('\P y.\T.all w.exists z.T(exist x.P(x, y), z, w)')]
        dynamic_library, _ = build_dynamic_library(exprs)
        dynamic_library = nltk_sig_to_coq_lib(dynamic_library)
        expected_dynamic_library = \
          ['Parameter P : Entity -> (Entity -> Prop).',
           'Parameter T : Prop -> (Entity -> (Entity -> Prop)).',
           'Parameter w : Entity.',
           'Parameter x : Entity.',
           'Parameter y : Entity.',
           'Parameter z : Entity.']
        for item in dynamic_library:
            self.assertIn(item, expected_dynamic_library)
        self.assertEqual(len(expected_dynamic_library), len(dynamic_library))

if __name__ == '__main__':
    suite1  = unittest.TestLoader().loadTestsFromTestCase(combine_signatures_or_rename_predsTestCase)
    suite2  = unittest.TestLoader().loadTestsFromTestCase(build_arbitrary_dynamic_libraryTestCase)
    suite3  = unittest.TestLoader().loadTestsFromTestCase(build_dynamic_libraryTestCase)
    suite4  = unittest.TestLoader().loadTestsFromTestCase(Coq2NLTKTypesTestCase)
    suite5  = unittest.TestLoader().loadTestsFromTestCase(Coq2NLTKSignaturesTestCase)
    suite6  = unittest.TestLoader().loadTestsFromTestCase(ArbiAutoTypesTestCase)
    suites  = unittest.TestSuite([suite1, suite2, suite3, suite4, suite5, suite6])
    unittest.TextTestRunner(verbosity=2).run(suites)
