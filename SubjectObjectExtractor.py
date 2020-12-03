import spacy
from spacy.tokens import Doc

SUBJECTS = ["nsubj", "nsubjpass", "csubj", "csubjpass", "agent", "expl"]
OBJECTS = ["dobj", "dative", "attr", "oprd"]

class SubjectObjectExtractor(object):

    def __init__(self, nlp):
        self.nlp = nlp
        Doc.set_extension('svos', default=None)
        pass

    def __call__(self, doc):
        doc._.svos = self.findSVOs(doc)
        return doc


    def getNounsFromConjunctions(self, nouns, labels):
        more_nouns = []
        for noun in nouns:
            right_dependencies = list(noun.rights)
            right_children = {child.lower_ for child in right_dependencies}
            if "and" in right_children:
                more_nouns.extend([child for child in right_dependencies if child.dep_ in labels or child.pos_ == "NOUN"])
                if len(more_nouns) > 0:
                    more_nouns.extend(self.getNounsFromConjunctions(more_nouns, labels))
        return more_nouns

    def getVerbsFromConjunctions(self, verbs):
        moreVerbs = []
        for verb in verbs:
            right_children = {child.lower_ for child in verb.rights}
            if "and" in right_children:
                moreVerbs.extend([child for child in verb.rights if child.pos_ == "VERB"])
                if len(moreVerbs) > 0:
                    moreVerbs.extend(self.getVerbsFromConjunctions(moreVerbs))
        return moreVerbs

    def findSubjects(self, token):
        head = token.head
        while head.pos_ != "VERB" and head.pos_ != "NOUN" and head.head != head:
            head = head.head
        if head.pos_ == "VERB":
            subs = [child for child in head.lefts if child.dep_ == "SUB"]
            if len(subs) > 0:
                verbNegated = self.isNegated(head)
                subs.extend(self.getNounsFromConjunctions(subs, SUBJECTS))
                return subs, verbNegated
            elif head.head != head:
                return self.findSubjects(head)
        elif head.pos_ == "NOUN":
            return [head], self.isNegated(token)
        return [], False

    def isNegated(self, token):
        negations = {"no", "not", "n't", "never", "none"}
        for child in list(token.lefts) + list(token.rights):
            if child.lower_ in negations:
                return True
            if child.head.dep_ == 'ROOT' and (list(child.lefts) or list(child.rights)):
                return self.isNegated(child)
        return False

    def findSVs(self, text):
        doc = self.nlp(text)
        subjects = []
        verbs = [token for token in doc if token.pos_  in ['VERB', 'AUX']]
        for verb in verbs:
            subs, verbNegated = self.getAllSubs(verb)
            if len(subs) > 0:
                for sub in subs:
                    subjects.append((sub.orth_, "!" + verb.orth_ if verbNegated else verb.orth_))
        return subjects

    def getObjsFromPrepositions(self, dependencies):
        objs = []
        for dependency in dependencies:
            if dependency.pos_ == "ADP" and dependency.dep_ == "prep":
                objs.extend([tok for tok in dependency.rights if tok.dep_  in OBJECTS or (tok.pos_ == "PRON" and tok.lower_ == "me")])
        return objs

    def getObjsFromAttrs(self, dependencies):
        for dependency in dependencies:
            if dependency.pos_ == "NOUN" and dependency.dep_ == "attr":
                verbs = [tok for tok in dependency.rights if tok.pos_ == "VERB"]
                if len(verbs) > 0:
                    for verb in verbs:
                        right_children = list(verb.rights)
                        objs = [tok for tok in right_children if tok.dep_ in OBJECTS]
                        objs.extend(self.getObjsFromPrepositions(right_children))
                        if len(objs) > 0:
                            return verb, objs
        return None, None

# I wanted to kill him with a hammer -> i, wanted, to kill him
    def getObjPhraseFromXComp(self, dependencies):
        for dependency in dependencies:
            if dependency.pos_ == "VERB" and dependency.dep_ == "xcomp":
                verb = dependency
                left_children = list(verb.lefts)
                right_children = list(verb.rights)
                subjects = [token for token in left_children if token.dep_ in SUBJECTS]
                objs = [token for token in right_children if token.dep_ in OBJECTS]
                objs.extend(self.getObjsFromPrepositions(right_children))
                if len(subjects) > 0 and len(objs) > 0:
                    return subjects + [verb] + objs
        return None

    def getObjFromXComp(self, dependencies):
        for dependency in dependencies:
            if dependency.pos_ == "VERB" and dependency.dep_ == "xcomp":
                verb = dependency
                right_children = list(verb.rights)
                objs = [token for token in right_children if token.dep_ in OBJECTS]
                objs.extend(self.getObjsFromPrepositions(right_children))
                if len(objs) > 0:
                    return verb, objs
        return None, None

    def getAllSubs(self, verb):
        verbNegated = self.isNegated(verb)
        subjects = [token for token in verb.lefts if token.dep_ in SUBJECTS and token.pos_ != "DET"]
        if len(subjects) > 0:
            subjects.extend(self.getNounsFromConjunctions(subjects, SUBJECTS))
        else:
            foundSubs, verbNegated = self.findSubjects(verb)
            subjects.extend(foundSubs)
        return subjects, verbNegated


    def getAllObjs(self, verb):
        right_children = list(verb.rights)
        objs = [token for token in right_children if token.dep_ in OBJECTS]
        objs.extend(self.getObjsFromPrepositions(right_children))

        potentialNewVerb, potentialNewObjs = self.getObjFromXComp(right_children)
        if potentialNewVerb is not None and potentialNewObjs is not None and len(potentialNewObjs) > 0:
            objs.extend(potentialNewObjs)
            verb = potentialNewVerb
        if len(objs) > 0:
            objs.extend(self.getNounsFromConjunctions(objs, OBJECTS))
        return verb, objs

    def findSVOs(self, doc):
        svos = []
        verbs = [token for token in doc if token.pos_  in ['VERB', 'AUX']]
        for verb in verbs:
            subjects, verbNegated = self.getAllSubs(verb)
            # Don't process sentences without a subject
            if len(subjects) > 0:
                # new_verb, objects = self.getAllObjs(verb)
                new_verb, objects = self.getAllObjs(verb)
                for sub in subjects:
                    for obj in objects:
                        objNegated = self.isNegated(obj)
                        # svos.append((sub.lower_, "!" + new_verb.lower_ if verbNegated or objNegated else verb.lower_, obj.lower_))
                        svos.append((sub.lower_, "!" + verb.lower_ if verbNegated or objNegated else verb.lower_, obj.lower_))
        return svos

    def printDeps(self, doc):
        for token in doc:
            print(token.orth_, token.dep_, token.pos_, token.head.orth_, 
                [left_child.orth_ for left_child in token.lefts], 
                [right_child.orth_ for right_child in token.rights])

