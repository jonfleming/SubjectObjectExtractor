import spacy
from spacy.tokens import Doc

SUBJECTS = ['nsubj', 'nsubjpass', 'csubj', 'csubjpass', 'agent', 'expl']
OBJECTS = ['dobj', 'dative', 'attr', 'oprd', 'pobj']

class SubjectObjectExtractor(object):
    adj_as_object = False

    def __init__(self, nlp):
        self.nlp = nlp

    def __call__(self, doc):
        doc._.svos = self.find_svos(doc)
        return doc

    def first(self, list):
        if len(list) > 0:
            return list[0]
        else:
            return None

    def get_nouns_from_conjunctions(self, nouns, labels):
        more_nouns = []
        for noun in nouns:
            right_dependencies = list(noun.rights)
            right_children = {child.lower_ for child in right_dependencies}
            if 'and' in right_children:
                dependency = self.first([child for child in right_dependencies if child.dep_ in labels or child.pos_ == 'NOUN'])
                if dependency:
                    if hasattr(noun, 'preposition'):
                        phrase = Phrase(noun.preposition.text + ' ' + dependency.text)
                    else:
                        phrase = PossPhrase(dependency)
                    
                    more_nouns.extend([phrase])
        return more_nouns

    def get_objects_from_conjunctive_verb(self, verbs):
        objects = []
        for verb in verbs:
            right_children = {child.lower_ for child in verb.rights}
            if 'and' in right_children:
                new_verbs = self.first([child for child in verb.rights if child.pos_ == 'VERB'])
                if new_verbs is not None:
                    obj = self.get_all_objects(new_verbs)
                    objects.extend(obj)
        return objects

    def find_subjects(self, token):
        head = token.head
        while head.pos_ != 'VERB' and head.pos_ != 'NOUN' and head.head != head:
            head = head.head
        if head.pos_ == 'VERB':
            subs = [child for child in head.lefts if child.dep_ in SUBJECTS]
            if len(subs) > 0:
                verb_negated = self.is_negated(head)
                subs.extend(self.get_nouns_from_conjunctions(subs, SUBJECTS))
                return subs, verb_negated
            elif head.head != head:
                return self.find_subjects(head)
        elif head.pos_ == 'NOUN':
            return [head], self.is_negated(token)
        return [], False

    def is_negated(self, token):
        negations = {'no', 'not', 'n\'t', 'never', 'none'}
        for child in list(token.children):
            if child.lower_ in negations:
                return True
            if child.head.dep_ == 'ROOT' and (list(child.lefts) or list(child.rights)):
                return self.is_negated(child)
        return False

    def get_objects_from_prepositions(self, dependencies):
        objects = []
        for dependency in dependencies:
            if dependency.pos_ == 'ADP':
                pobj = self.first([token for token in dependency.rights if token.dep_  in OBJECTS or (token.pos_ == 'PRON' and token.lower_ == 'me')])
                if pobj is not None:
                    obj = PrepPhrase(dependency, pobj)
                    objects.extend([obj])
        return objects

    def get_object_from_verb_phrase(self, dependencies):
        objects = []
        for dependency in dependencies:
            if dependency.pos_ == 'VERB':
                prep = self.first([token for token in dependency.lefts if token.pos_ == 'PART'])
                if prep is not None:
                    obj = PrepPhrase(prep, dependency)
                    objects.extend([obj])
        return objects

    def get_objects_from_attributess(self, dependencies):
        for dependency in dependencies:
            if dependency.pos_ == 'NOUN' and dependency.dep_ == 'attr':
                verbs = [token for token in dependency.rights if token.pos_ == 'VERB']
                if len(verbs) > 0:
                    for verb in verbs:
                        right_children = list(verb.rights)
                        objects = [token for token in right_children if token.dep_ in OBJECTS]
                        objects.extend(self.get_objects_from_prepositions(right_children))
                        if len(objects) > 0:
                            return verb, objects
        return None, None

    def get_object_phrase_from_xcomp(self, dependencies):
        for dependency in dependencies:
            if dependency.pos_ == 'VERB' and dependency.dep_ == 'xcomp':
                verb = dependency
                left_children = list(verb.lefts)
                right_children = list(verb.rights)
                subjects = [token.text for token in left_children if token.dep_ in SUBJECTS or token.dep_ == 'aux']
                objects = [token.text for token in right_children if token.dep_ in OBJECTS]

                if len(subjects) > 0 and len(objects) > 0:                    
                    text = ''.join(subjects) + ' ' + verb.text + ' ' + ''.join(objects)
                    obj = Phrase(text)
                    return [obj]
        return None

    def get_object_from_xcomp(self, dependencies):
        for dependency in dependencies:
            if dependency.pos_ == 'VERB' and dependency.dep_ == 'xcomp':
                verb = dependency
                right_children = list(verb.rights)
                objects = [token for token in right_children if token.dep_ in OBJECTS]
                objects.extend(self.get_objects_from_prepositions(right_children))
                if len(objects) > 0:
                    return verb, objects
        return None, None

    def get_all_subjects(self, verb):
        verb_negated = self.is_negated(verb)
        subjects = [token for token in verb.lefts if token.dep_ in SUBJECTS and token.pos_ != 'DET']
        if len(subjects) > 0:
            subjects.extend(self.get_nouns_from_conjunctions(subjects, SUBJECTS))
        else:
            foundSubs, verb_negated = self.find_subjects(verb)
            subjects.extend(foundSubs)
        return subjects, verb_negated


    def get_all_objects(self, verb):
        right_children = list(verb.rights)
        objects = [token for token in right_children if token.dep_ in OBJECTS]
        if self.adj_as_object:
            adjectives = [token for token in verb.rights if token.pos_ in ['ADJ']]
            objects.extend(adjectives)

        objects.extend(self.get_objects_from_prepositions(right_children))
        objects.extend(self.get_object_from_verb_phrase(right_children))
        new_object = self.get_object_phrase_from_xcomp(right_children)

        if new_object:
            objects.extend(new_object)
        if len(objects) > 0 and new_object is None:
            objects.extend(self.get_nouns_from_conjunctions(objects, OBJECTS))

        return objects

    def get_predicate(self, verb, negated):
        aux = self.first([token for token in verb.lefts if token.dep_ in ['aux','auxpass']])
        predicate = 'not ' + verb.lower_ if negated else verb.lower_
        if aux is not None:
            predicate = aux.lower_ + ' ' + predicate if aux else predicate
        return predicate

    def find_svs(self, doc):
        svs = []
        verbs = [token for token in doc if token.pos_  in ['VERB', 'AUX']]
        for verb in verbs:
            subjects, verb_negated = self.get_all_subjects(verb)
            if len(subjects) > 0:
                for subject in subjects:
                    predicate = self.get_predicate(verb, verb_negated)
                    svs.append((subject.lower_, predicate))
        return svs

    def find_svos(self, doc):
        svos = []
        verbs = [token for token in doc if token.pos_  in ['VERB','AUX'] and token.dep_ != 'xcomp' ]

        for verb in verbs:
            subjects, verb_negated = self.get_all_subjects(verb)
            if len(subjects) > 0:
                objects = self.get_all_objects(verb)
                if not objects:
                    conjunctive_verbs = [verb] + [token for token in verb.rights if token.pos_ == 'VERB']
                    objects = self.get_objects_from_conjunctive_verb(conjunctive_verbs)
                
                for subject in subjects:
                    for obj in objects:
                        obj_negated = self.is_negated(obj)
                        predicate = self.get_predicate(verb, verb_negated or obj_negated)
                        svos.append((subject.lower_, predicate, obj.lower_))
        return svos

    def printDeps(self, doc):
        for token in doc:
            print(token.text, token.dep_, token.pos_, token.head.text, 
                [left_child.text for left_child in token.lefts], 
                [right_child.text for right_child in token.rights])
class Phrase(object):
    def __init__(self, text):
        self.text = text
        self.lower_ = self.text.lower()
        self.children = []
        self.lefts = []
        self.rights = []
class PrepPhrase(object):
    def __init__(self, preposition, pobj):
        self.preposition = preposition
        self.text = preposition.text + ' ' + pobj.text
        self.lower_ = self.text.lower()
        self.children = []
        self.lefts = []
        self.rights = pobj.rights

class PossPhrase(object):
    def __init__(self, noun):
        lefts = [token for token in noun.lefts if token.dep_ == 'poss']
        if lefts:
            self.posessive = lefts[0]
            self.text = self.posessive.text + ' ' + noun.text
        else:
            self.text = noun.text

        self.lower_ = self.text.lower()
        self.children = []
        self.lefts = noun.lefts
        self.rights = noun.rights