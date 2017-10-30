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

import codecs
from collections import defaultdict
import logging
import re

from nltk import Tree
from nltk.compat import string_types
from nltk.sem.logic import ENTITY_TYPE
from nltk.sem.logic import TRUTH_TYPE
from nltk.sem.logic import EVENT_TYPE
from nltk.sem.logic import ANY_TYPE
from nltk.sem.logic import AbstractVariableExpression
from nltk.sem.logic import ComplexType
from nltk.sem.logic import ConstantExpression
from nltk.sem.logic import InconsistentTypeHierarchyException
from nltk.sem.logic import LogicalExpressionException
from nltk.sem.logic import Variable
from nltk.sem.logic import typecheck

from knowledge import get_tokens_from_xml_node
from logic_parser import lexpr
from normalization import normalize_token
from tree_tools import tree_or_string

def linearize_type(pred_type):
    linearized_type = []
    if not pred_type.__dict__:
        if str(pred_type) == 'e':
            type_str = 'Entity'
        elif str(pred_type) == 'v':
            type_str = 'Event'
        else:
            type_str = 'Prop'
        linearized_type = [type_str]
    else:
        linearized_type.extend(linearize_type(pred_type.first))
        linearized_type.extend(linearize_type(pred_type.second))
    return linearized_type

def type_length(expr_type):
    """
    Counts the number of parameters of a predicate. E.g.
    type_length(e) = 1
    type_length(<e, t>) = 2
    type_length(<e, <e,t>>) = 3
    """
    acc_first, acc_second = 0, 0
    if 'first' not in expr_type.__dict__ \
       and 'second' not in expr_type.__dict__:
        return 1
    if 'first' in expr_type.__dict__:
        acc_first = type_length(expr_type.first)
    if 'second' in expr_type.__dict__:
        acc_second = type_length(expr_type.second)
    return acc_first + acc_second

def resolve_types_in_signature(signature):
    signature = {k : v for k, v in signature.items() if v is not None}
    for predicate, pred_type in signature.items():
        pred_type_str = str(pred_type)
        pred_type_str_resolved = re.sub(r'\?', r't', pred_type_str)
        signature[predicate] = read_type(pred_type_str_resolved)
    return signature

def remove_colliding_predicates(signature, expr):
    resolution_success = False
    i = 0
    while (not resolution_success):
        try:
            expr.typecheck(signature)
            resolution_success = True
        except InconsistentTypeHierarchyException as e:
            e_str = str(e)
            # The exception message is of the form:
            # The variable ''s' was found in ... (referring to variable 's).
            variable_name = re.findall(r"'(\S+?)'", e_str)[0]
            signature.pop(variable_name, None)
            if variable_name == 'TrueP':
                break
        except AttributeError as e:
            break
        i += 1
        if i > 100:
            logging.info('There is probably a problem in the typecheck resolution of ' \
                    'expression {0} with signature {1}'.format(str(expr), signature))
            break
    try:
        signature = expr.typecheck(signature)
    except InconsistentTypeHierarchyException as e:
        e_str = str(e)
        variable_name = re.findall(r"'(\S+?)'", e_str)[0]
        signature.pop(variable_name, None)
    except AttributeError as e:
        logging.info('There is probably a problem in the typecheck resolution of ' \
            'expression {0} with signature {1}'.format(str(expr), signature))
    return signature

def combine_signatures_(signatures):
    """
    Combinator function necessary for .visit method.
    If one predicate is resolved as different types, only the shortest
    (less complex) type is finally assigned.
    """
    combined_signature = {}
    for signature in signatures:
        for predicate, predicate_sig in signature.items():
            if predicate not in combined_signature:
                combined_signature[predicate] = predicate_sig
            else:
                sig_length_previous = type_length(combined_signature[predicate])
                sig_length_new = type_length(predicate_sig)
                if sig_length_new > sig_length_previous:
                    combined_signature[predicate] = predicate_sig
    return combined_signature

def resolve_types_(expr, signature=None):
    try:
        return resolve_types_in_signature(expr.typecheck())
    except InconsistentTypeHierarchyException:
        pass
    if signature is None:
        signature = {}
    if isinstance(expr, ConstantExpression) or \
       isinstance(expr, AbstractVariableExpression) or \
       isinstance(expr, Variable):
        return resolve_types_in_signature(expr.typecheck())
    elif isinstance(expr, NegatedExpression):
        return resolve_types_in_signature(expr.term.typecheck())
    elif isinstance(expr, BinaryExpression):
        child_exprs = [expr.first,  expr.second]
        signatures = [resolve_types(e) for e in child_exprs]
    elif isinstance(expr, ApplicationExpression):
        func, args = expr.uncurry()
        child_exprs = [func] + args
    elif isinstance(expr, VariableBinderExpression):
        child_exprs = [expr.variable,  expr.term]
    else:
        raise NotImplementedError(
            'Expression not recognized: {0}, type: {1}'.format(expr, type(expr)))
    signatures = [resolve_types(e) for e in child_exprs]

    # elif isinstance(expr, NegatedExpression):
    #     G.graph['head_node'] = next(node_id_gen)
    #     G.add_node(G.graph['head_node'], label='not', type='op')
    #     graphs = map(formula_to_tree, [expr.term])
    #     G = merge_graphs_to(G, graphs)
    # elif isinstance(expr, VariableBinderExpression):
    #     quant = '<quant_unk>'
    #     if isinstance(expr, QuantifiedExpression):
    #         quant = expr.getQuantifier()
    #         type = 'quantifier'
    #     elif isinstance(expr, LambdaExpression):
    #         quant = 'lambda'
    #         type = 'binder'
    #     G.graph['head_node'] = next(node_id_gen)
    #     G.add_node(G.graph['head_node'], label=quant, type=type)
    #     var_node_id = next(node_id_gen)
    #     G.add_node(var_node_id, label=str(expr.variable), type='variable')
    #     G.add_edge(G.graph['head_node'], var_node_id, type='var_bind')
    #     graphs = map(formula_to_tree, [expr.term])
    #     G = merge_graphs_to(G, graphs)
    # return G
    return signatures

def resolve_types_(expr, signature = {}):
    """
    Function that is used to traverse the structure of a NLTK formula
    and infer types bottom up, resolving unknowns '?' into 't' (Prop).
    """
    if isinstance(expr, ConstantExpression) or \
       isinstance(expr, AbstractVariableExpression):
        return expr.typecheck(), expr
    signature = expr.visit(lambda e: resolve_types(e, signature),
                           lambda parts: combine_signatures(parts))
    signature = remove_reserved_predicates(signature)
    signature = remove_colliding_predicates(signature, expr)
    signature = remove_reserved_predicates(signature)
    signature = resolve_types_in_signature(signature)
    return signature

def combine_signatures_safe(signatures):
    """
    Combinator function necessary for .visit method.
    If one predicate is resolved as different types, only the shortest
    (less complex) type is finally assigned.
    """
    combined_signature = defaultdict(list)
    for signature in signatures:
        for predicate, predtypes_exprs in signature.items():
            # from pudb import set_trace; set_trace()
            for predtype, expr in predtypes_exprs:
                combined_signature[predicate].append((predtype, expr))
    # for pred, sigs_exprs in combined_signature:
    #     if len(sigs_exprs) > 1 and len(set(pred_type for (pred_type, expr) in sigs_exprs)) > 1:
    #         for pred_type, expr in sigs_exprs:
    #             new_pred_name = make_new_pred_name(pred, pred_type)
    #             combined_signature[predicate].append((pred_type, expr))
    return combined_signature

def convert_to_multitypes(signature, expr):
    multi_signature = defaultdict(list)
    for k, v in signature.items():
        multi_signature[k].append((v, expr))
    return multi_signature

def resolve_types_rec(expr, signature=None):
    """
    Function that is used to traverse the structure of a NLTK formula
    and infer types bottom up, resolving unknowns '?' into 't' (Prop).
    """
    if signature is None:
        signature = defaultdict(list)
    try:
        signature = convert_to_multitypes(expr.typecheck(), expr)
    except InconsistentTypeHierarchyException as e:
        if isinstance(expr, ConstantExpression) or \
           isinstance(expr, AbstractVariableExpression):
            signature = convert_to_multitypes(expr.typecheck(), expr)
        else:
            signature = expr.visit(lambda e: resolve_types_rec(e, signature),
                                   lambda parts: combine_signatures_safe(parts))
    return signature

def rename_guided(expr, resolution_guide):
    """
    resolution_guide is a dictionary whose keys are expressions
    and values are tuples (previous_pred, new_pred) that guide
    the renaming.
    """
    # from pudb import set_trace; set_trace()
    if expr in resolution_guide:
        prev_pred, new_pred = resolution_guide[expr]
        return expr.replace(Variable(prev_pred), lexpr(new_pred))
    return expr

def make_new_pred_name(pred, pred_type):
    type_len = type_length(pred_type)
    # from pudb import set_trace; set_trace()
    if type_len > 2:
        pred_name = '{0}_{1}'.format(str(pred), type_len)
    elif type_len == 2:
        pred_name = '{0}_{1}'.format(str(pred), str(pred_type.first))
    else:
        pred_name = '{0}_{1}'.format(str(pred), str(pred_type))
    return pred_name

resolution_guide = {}

def resolve_types_and_rename_collisions(expr, signature = {}):
    """
    Function that is used to traverse the structure of a NLTK formula
    and infer types bottom up, resolving unknowns '?' into 't' (Prop).
    """
    global resolution_guide
    signature = resolve_types_rec(expr, signature)

    resolution_guide = {}
    for pred, sigs_exprs in signature.items():
        if len(sigs_exprs) > 1 and len(set(pred_type for (pred_type, _) in sigs_exprs)) > 1:
            for pred_type, ex in sigs_exprs:
                new_pred_name = make_new_pred_name(pred, pred_type)
                resolution_guide[ex] = (pred, new_pred_name)

    expr = expr.visit_structured(
        lambda e: rename_guided(e, resolution_guide),
        expr.__class__)
    signature = expr.typecheck()

    signature = remove_reserved_predicates(signature)
    # signature = remove_colliding_predicates(signature, expr)
    # signature = remove_reserved_predicates(signature)
    signature = resolve_types_in_signature(signature)
    return signature, expr

def combine_signatures_or_rename_preds(unused, exprs, preferred_sig=None):
    """
    `signatures` is a list of dictionaries. Each dictionary has key-value
      pairs where key is a predicate name, and value is a type object.
    `exprs` are logical formula objects.
    This function return a single signature dictionary with merged signatures.
    If there is a predicate for which there are differing types, then the
    predicate is renamed and each version is associated to a different type
    in the signature dictionary. The target predicate is also renamed in
    the logical expressions.
    """
    global resolution_guide

    signatures = [resolve_types_rec(expr) for expr in exprs]
    signature = defaultdict(list)
    for s in signatures:
        for k, v in s.items():
            signature[k].extend(v)
    
    resolution_guide = {}
    for pred, sigs_exprs in signature.items():
        if len(sigs_exprs) > 1 and len(set(pred_type for (pred_type, _) in sigs_exprs)) > 1:
            for pred_type, ex in sigs_exprs:
                new_pred_name = make_new_pred_name(pred, pred_type)
                resolution_guide[ex] = (pred, new_pred_name)

    new_exprs = []
    for expr in exprs:
        expr = expr.visit_structured(
            lambda e: rename_guided(e, resolution_guide),
            expr.__class__)
        new_exprs.append(expr)
    signature = typecheck(new_exprs)

    signature = remove_reserved_predicates(signature)
    # signature = remove_colliding_predicates(signature, expr)
    # signature = remove_reserved_predicates(signature)
    try:
        signature = resolve_types_in_signature(signature)
    except:
        from pudb import set_trace; set_trace()
    return signature, new_exprs


def resolve_types(expr, signature = {}):
    """
    Function that is used to traverse the structure of a NLTK formula
    and infer types bottom up, resolving unknowns '?' into 't' (Prop).
    """
    global resolution_guide
    signature = resolve_types_rec(expr, signature)

    resolution_guide = {}
    for pred, sigs_exprs in signature.items():
        if len(sigs_exprs) > 1 and len(set(pred_type for (pred_type, _) in sigs_exprs)) > 1:
            for pred_type, ex in sigs_exprs:
                new_pred_name = make_new_pred_name(pred, pred_type)
                resolution_guide[ex] = (pred, new_pred_name)

    expr = expr.visit_structured(
        lambda e: rename_guided(e, resolution_guide),
        expr.__class__)
    signature = expr.typecheck()

    signature = remove_reserved_predicates(signature)
    # signature = remove_colliding_predicates(signature, expr)
    # signature = remove_reserved_predicates(signature)
    signature = resolve_types_in_signature(signature)
    return signature

def remove_reserved_predicates(signature):
    """
    Some predicates are already defined in coq, and they are not necessary
    to handle here. Moreover, predicates like AND or OR would be difficult
    to handle in this context, because they may have different types in the
    same formuli.
    """
    reserved_predicates = ['AND', 'OR', 'TrueP']
    for reserved_predicate in reserved_predicates:
        if reserved_predicate in signature:
            del signature[reserved_predicate]
    return signature

def get_dynamic_library_from_doc(doc, semantics_nodes):
    # Each type is of the form "predicate : basic_type -> ... -> basic_type."
    # semantics_nodes = doc.xpath('./sentences/sentence/semantics[1]')
    types_sets = []
    for semantics_node in semantics_nodes:
      types = set(semantics_node.xpath('./span/@type'))
      types_sets.append(types)
    coq_libs = [['Parameter {0}.'.format(t) for t in types] for types in types_sets]
    nltk_sigs_arbi = [convert_coq_signatures_to_nltk(coq_lib) for coq_lib in coq_libs]
    formulas = [sem.xpath('./span[1]/@sem')[0] for sem in semantics_nodes]
    formulas = parse_exprs_if_str(formulas)
    nltk_sig_arbi, formulas = combine_signatures_or_rename_preds(nltk_sigs_arbi, formulas)
    nltk_sig_auto, formulas = build_dynamic_library(formulas, nltk_sig_arbi)
    # coq_static_lib_path is useful to get reserved predicates.
    # ccg_xml_trees is useful to get full list of tokens
    # for which we need to specify types.
    dynamic_library = merge_dynamic_libraries(
        nltk_sig_arbi,
        nltk_sig_auto,
        coq_static_lib_path='coqlib.v', 
        doc=doc)
    dynamic_library_str = '\n'.join(sorted(dynamic_library))
    return dynamic_library_str, formulas

def build_library_entry(predicate, pred_type):
    """
    Creates a library entry out of a pair (predicate, pred_type),
    where pred_type is a tree such as <e, t> or <e, <e, t>>, etc.
    It returns a string of the form
    "Parameter pred : Entity -> Prop."
    """
    type_str = str(pred_type).replace(
        '<', '(').replace(
        '>', ')').replace(
        ',', ' -> ').replace(
        't', 'Prop').replace(
        'e', 'Entity').replace(
        'v', 'Event')
    if type_str.endswith(')'):
       type_str = type_str[1:-1]
    library_entry = 'Parameter ' \
                  + predicate \
                  + ' : ' \
                  + type_str \
                  + '.'
    return library_entry

def build_library_entry_(predicate, pred_type):
    """
    Creates a library entry out of a pair (predicate, pred_type),
    where pred_type is a tree such as <e, t> or <e, <e, t>>, etc.
    It returns a string of the form
    "Parameter pred : Entity -> Prop."
    """
    linearized_type = linearize_type(pred_type)
    library_entry = 'Parameter ' \
                  + predicate \
                  + ' : ' \
                  + ' -> '.join(linearized_type) \
                  + '.'
    return library_entry

def parse_exprs_if_str(exprs):
    """
    If expressions are strings, convert them into logic formulae.
    """
    exprs_logic = []
    for expr in exprs:
        if isinstance(expr, str):
            exprs_logic.append(lexpr(expr))
        else:
            exprs_logic.append(expr)
    return exprs_logic

def build_dynamic_library(exprs, preferred_signature=None):
    """
    Create a dynamic library with types of objects that appear in coq formulae.
    Optionally, it may receive partially specified signatures for objects
    using the format by NLTK (e.g. {'_john' : e, '_mary' : e, '_love' : <e,<e,t>>}).
    """
    # If expressions are strings, convert them into logic formulae.
    exprs_logic = parse_exprs_if_str(exprs)
    signatures = [resolve_types(e) for e in exprs_logic]
    signature, exprs = combine_signatures_or_rename_preds(
        signatures, exprs_logic, preferred_signature)
    signature = remove_reserved_predicates(signature)
    return signature, exprs

def combine_signatures_or_rename_preds_(signatures, exprs, preferred_sig=None):
    """
    `signatures` is a list of dictionaries. Each dictionary has key-value
      pairs where key is a predicate name, and value is a type object.
    `exprs` are logical formula objects.
    This function return a single signature dictionary with merged signatures.
    If there is a predicate for which there are differing types, then the
    predicate is renamed and each version is associated to a different type
    in the signature dictionary. The target predicate is also renamed in
    the logical expressions.
    """
    assert len(signatures) == len(exprs), '{0} vs. {1}'.format(signatures, exprs)
    signatures_merged = {}
    exprs_new = []
    for i, (signature, expr) in enumerate(zip(signatures, exprs)):
        expr_new = expr
        for pred, typ in signature.items():
            if preferred_sig is not None and pred in preferred_sig:
                continue
            if pred not in signatures_merged:
                signatures_merged[pred] = typ
            else:
                if typ != signatures_merged[pred]:
                    pred_new = pred + '_' + str(i)
                    signatures_merged[pred_new] = typ
                    expr_new = expr_new.replace(Variable(pred), lexpr(pred_new))
        exprs_new.append(expr_new)
    return signatures_merged, exprs_new

def convert_coq_to_nltk_type(coq_type):
    """
    Given a coq_type specification such as:
      Parameter _love : Entity -> Entity -> Prop.
    return the equivalent NLTK type specification:
      {'_love' : read_type('<e, <e, t>>')}
    """
    assert isinstance(coq_type, str)
    coq_type_list = coq_type.split()
    assert len(coq_type_list) >= 4, 'Wrong coq_type format: %s' % coq_type
    parameter, surface, colon = coq_type_list[:3]
    assert parameter == 'Parameter' and colon == ':'
    # This list contains something like ['Entity', '->', 'Prop', '->', 'Prop'...]
    type_sig = coq_type_list[3:]
    nltk_type_str = ' '.join(type_sig).rstrip('.').replace(
        '->', ' ').replace(
        'Entity', 'e').replace(
        'Prop', 't').replace(
        'Event', 'v')
    if not nltk_type_str.startswith('(') or not nltk_type_str.endswith('('):
        nltk_type_str = '(' + nltk_type_str + ')'
    # Add pre-terminals (necessary for NLTK, if we convert to CNF).
    nltk_type_str = re.sub(r'([evt])', r'(N \1)', nltk_type_str)
    nltk_type_tree = tree_or_string(nltk_type_str)
    nltk_type_tree.chomsky_normal_form(factor='right')
    nltk_type_str = remove_labels_and_unaries(nltk_type_tree).replace(
        '( ', '(').replace(
        '(', '<').replace(
        ')', '>').replace(
        ' ', ',')
    if len(type_sig) == 1:
        nltk_type_str = nltk_type_str.strip('<>')
    return {surface : read_type(nltk_type_str)}

def remove_labels_and_unaries(tree):
    assert isinstance(tree, Tree)
    leaf_treepos = tree.treepositions(order='leaves')
    for p in tree.treepositions():
        if p not in leaf_treepos and p != ():
            tree[p].set_label('')
            if len(tree[p]) == 1:
                tree[p] = tree[p][0]
    return str(tree)

def convert_coq_to_nltk_type_(coq_type):
    """
    Given a coq_type specification such as:
      Parameter _love : Entity -> Entity -> Prop.
    return the equivalent NLTK type specification:
      {'_love' : read_type('<e, <e, t>>')}
    """
    assert isinstance(coq_type, str)
    coq_type_list = coq_type.split()
    assert len(coq_type_list) >= 4, 'Wrong coq_type format: %s' % coq_type
    parameter, surface, colon = coq_type_list[:3]
    assert parameter == 'Parameter' and colon == ':'
    # This list contains something like ['Entity', '->', 'Prop', '->', 'Prop'...]
    type_sig = coq_type_list[3:]
    type_ids = []
    for i, type_item in enumerate(type_sig):
        assert (i % 2 == 1) == (type_item == '->')
        if type_item.startswith('Entity'):
            type_ids.append('e')
        elif type_item.startswith('Prop'):
            type_ids.append('t')
        elif type_item.startswith('Event'):
            type_ids.append('v')
        elif type_item != '->':
            raise(ValueError('Invalid type name: %s in %s' % (type_item, coq_type)))
    assert len(type_ids) > 0
    if len(type_ids) == 1:
        nltk_type_str = type_ids[0]
    else:
        # Create a string like "<e, <t, t>>"
        nltk_type_str = '<' + ', <'.join(type_ids[:-1]) \
                      + ', ' + type_ids[-1] + '>' * len(type_ids)
    return {surface : read_type(nltk_type_str)}

def read_type(type_string):
    assert isinstance(type_string, string_types)
    type_string = type_string.replace(' ', '') #remove spaces

    if type_string[0] == '<':
        assert type_string[-1] == '>'
        paren_count = 0
        for i,char in enumerate(type_string):
            if char == '<':
                paren_count += 1
            elif char == '>':
                paren_count -= 1
                assert paren_count > 0
            elif char == ',':
                if paren_count == 1:
                    break
        return ComplexType(read_type(type_string[1  :i ]),
                           read_type(type_string[i+1:-1]))
    elif type_string[0] == "%s" % ENTITY_TYPE:
        return ENTITY_TYPE
    elif type_string[0] == "%s" % TRUTH_TYPE:
        return TRUTH_TYPE
    elif type_string[0] == "%s" % EVENT_TYPE:
        return EVENT_TYPE
    elif type_string[0] == "%s" % ANY_TYPE:
        return ANY_TYPE
    else:
        message="Unexpected character: '%s'." % type_string[0]
        raise ValueError(message)

def convert_coq_signatures_to_nltk(coq_sig):
    """
    Given a coq_library of type specifications such as:
      Parameter _love : Entity -> Entity -> Prop.
      Parameter _john : Entity.
      Parameter _mary : Entity.
    return the equivalent NLTK type specification:
      {'_love' : read_type('<e, <e, t>>'),
       '_john' : read_type('e'),
       '_mary' : read_type('e')}
    """
    assert isinstance(coq_sig, list)
    nltk_sig = {}
    nltk_types = []
    for coq_type in coq_sig:
        nltk_type = convert_coq_to_nltk_type(coq_type)
        nltk_sig.update(nltk_type)
    return nltk_sig

def get_coq_types(xml_node):
    types = xml_node.get('coq_type', None)
    if types is None or types == "":
        return []
    types = types.split(' ||| ')
    return types

def build_arbitrary_dynamic_library(ccg_trees):
    """
    Given a list of CCG trees whose root nodes are annotated with an
    attribute 'coq_type', it produces a list of entries for the dynamic
    library that is piped to coq. The output is something like:
    ["Parameter dog : Entity.", "Parameter walk : Entity -> Prop.", ...]
    """
    dynamic_library = []
    for ccg_tree in ccg_trees:
        coq_types = get_coq_types(ccg_tree)
        dynamic_library.extend(coq_types)
    dynamic_library = sorted(list(set(dynamic_library)))
    return dynamic_library

def get_reserved_preds_from_coq_static_lib(coq_static_lib_path):
    finput = codecs.open(coq_static_lib_path, 'r', 'utf-8')
    type_definitions = \
        [line.strip() for line in finput if line.startswith('Parameter ')]
    finput.close()
    reserved_predicates = \
        [type_definition.split()[1] for type_definition in type_definitions]
    return reserved_predicates

def get_predicate_type_from_library(predicate, lib):
    assert isinstance(lib, dict)
    return lib.get(predicate, None)

def merge_dynamic_libraries(sig_arbi, sig_auto, coq_static_lib_path, doc):
    reserved_predicates = get_reserved_preds_from_coq_static_lib(coq_static_lib_path)
    # Get base forms, unless the base form is '*', in which case get surf form.
    base_forms = get_tokens_from_xml_node(doc)
    required_predicates = set(normalize_token(t) for t in base_forms)
    sig_merged = sig_auto
    sig_merged.update(sig_arbi) # overwrites automatically inferred types.
    # Remove predicates that are reserved or not required (e.g. variables).
    preds_to_remove = set()
    preds_to_remove.update(reserved_predicates)
    for pred in sig_merged:
        if pred not in required_predicates and not re.match(r'\S+_[0-9]', pred):
            preds_to_remove.add(pred)
    for pred in preds_to_remove:
        if pred in sig_merged:
            del sig_merged[pred]
    # Convert into coq style library entries.
    dynamic_library = []
    for predicate, pred_type in sig_merged.items():
        library_entry = build_library_entry(predicate, pred_type)
        dynamic_library.append(library_entry)
    result_lib = list(set(dynamic_library))
    return result_lib

def merge_dynamic_libraries_(coq_lib, nltk_lib, coq_static_lib_path, doc):
    reserved_predicates = get_reserved_preds_from_coq_static_lib(coq_static_lib_path)
    # Get base forms, unless the base form is '*', in which case get surf form.
    base_forms = get_tokens_from_xml_node(doc)
    required_predicates = set(normalize_token(t) for t in base_forms)
    # required_predicates = set(normalize_token(t) for t in doc.xpath('//token/@base'))
    coq_lib_index = {coq_lib_entry.split()[1] : coq_lib_entry \
                       for coq_lib_entry in coq_lib}
    nltk_lib_index = {nltk_lib_entry.split()[1] : nltk_lib_entry \
                        for nltk_lib_entry in nltk_lib}
    result_lib = []
    for predicate in required_predicates:
        if predicate in reserved_predicates:
            continue
        coq_predicate_type = get_predicate_type_from_library(predicate, coq_lib_index)
        nltk_predicate_type = get_predicate_type_from_library(predicate, nltk_lib_index)
        if coq_predicate_type is not None:
            result_lib.append(coq_predicate_type)
        elif nltk_predicate_type is not None:
            result_lib.append(nltk_predicate_type)
    # Add possible renamed predicates for NLTK signature.
    for coq_style_entry in nltk_lib:
      if re.match(r'\S+_[0-9]', coq_style_entry.split()[1]):
        result_lib.append(coq_style_entry)
    result_lib = list(set(result_lib))
    return result_lib
