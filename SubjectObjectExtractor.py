import spacy
from spacy.tokens import Doc

SUBJECTS = ['nsubj', 'nsubjpass', 'csubj', 'csubjpass', 'agent', 'expl']
OBJECTS = ['dobj', 'dative', 'attr', 'oprd']

class SubjectObjectExtractor(object):
    def __init__(self, nlp):
        self.nlp = nlp

    def __call__(self, doc):
        doc._.svos = self.find_svos(doc)
        return doc


    def get_nouns_from_conjunctions(self, nouns, labels):
        more_nouns = []
        for noun in nouns:
            right_dependencies = list(noun.rights)
            right_children = {child.lower_ for child in right_dependencies}
            if 'and' in right_children:
                more_nouns.extend([child for child in right_dependencies if child.dep_ in labels or child.pos_ == 'NOUN'])
                if len(more_nouns) > 0:
                    more_nouns.extend(self.get_nouns_from_conjunctions(more_nouns, labels))
        return more_nouns

    def get_objects_from_conjunctive_verb(self, verbs):
        objects = []
        for verb in verbs:
            right_children = {child.lower_ for child in verb.rights}
            if 'and' in right_children:
                new_verbs = [child for child in verb.rights if child.pos_ == 'VERB']
                if new_verbs is not None:
                    _, obj = self.get_all_objects(new_verbs[0])
                    objects.extend(obj)
        return objects

    def find_subjects(self, token):
        head = token.head
        while head.pos_ != 'VERB' and head.pos_ != 'NOUN' and head.head != head:
            head = head.head
        if head.pos_ == 'VERB':
            subs = [child for child in head.lefts if child.dep_ in SUBJECTS]
            if len(subs) > 0:
                verbNegated = self.is_negated(head)
                subs.extend(self.get_nouns_from_conjunctions(subs, SUBJECTS))
                return subs, verbNegated
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
            if dependency.pos_ == 'ADP' and dependency.dep_ == 'prep':
                objects.extend([token for token in dependency.rights if token.dep_  in OBJECTS or (token.pos_ == 'PRON' and token.lower_ == 'me')])
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

# I wanted to kill him with a hammer -> i, wanted, to kill him
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
                    obj = _Token(text)
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
        verbNegated = self.is_negated(verb)
        subjects = [token for token in verb.lefts if token.dep_ in SUBJECTS and token.pos_ != 'DET']
        if len(subjects) > 0:
            subjects.extend(self.get_nouns_from_conjunctions(subjects, SUBJECTS))
        else:
            foundSubs, verbNegated = self.find_subjects(verb)
            subjects.extend(foundSubs)
        return subjects, verbNegated


    def get_all_objects(self, verb):
        right_children = list(verb.rights)
        objects = [token for token in right_children if token.dep_ in OBJECTS]
        objects.extend(self.get_objects_from_prepositions(right_children))
        new_object = self.get_object_phrase_from_xcomp(right_children)

        if new_object:
            objects.extend(new_object)
        if len(objects) > 0 and new_object is None:
            objects.extend(self.get_nouns_from_conjunctions(objects, OBJECTS))
        return verb, objects

    def find_svs(self, doc):
        subjects = []
        verbs = [token for token in doc if token.pos_  in ['VERB', 'AUX']]
        for verb in verbs:
            subjects, verbNegated = self.get_all_subjects(verb)
            if len(subjects) > 0:
                for subject in subjects:
                    subjects.append((subject.orth_, '!' + verb.orth_ if verbNegated else verb.orth_))
        return subjects

    def find_svos(self, doc):
        svos = []
        verbs = [token for token in doc if token.pos_  in ['VERB', 'AUX'] and token.dep_ != 'xcomp' ]
        for verb in verbs:
            subjects, verbNegated = self.get_all_subjects(verb)
            if len(subjects) > 0:
                new_verb, objects = self.get_all_objects(verb)
                if not objects:
                    conjunctive_verbs = [verb] + [token for token in verb.rights if token.pos_ == 'VERB']
                    objects = self.get_objects_from_conjunctive_verb(conjunctive_verbs)
                
                for subject in subjects:
                    for obj in objects:
                        objNegated = self.is_negated(obj)
                        svos.append((subject.lower_, '!' + verb.lower_ if verbNegated or objNegated else verb.lower_, obj.lower_))
        return svos

    def printDeps(self, doc):
        for token in doc:
            print(token.orth_, token.dep_, token.pos_, token.head.orth_, 
                [left_child.orth_ for left_child in token.lefts], 
                [right_child.orth_ for right_child in token.rights])

class _Token(object):
    def __init__(self, text):
        self.text = text
        self.lower_ = text.lower()
        self.children = []

