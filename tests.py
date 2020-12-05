import unittest
import spacy
from spacy.tokens import Doc
from SubjectObjectExtractor import SubjectObjectExtractor

nlp = spacy.load("en_core_web_md")
pipeline_component = SubjectObjectExtractor(nlp)
Doc.set_extension('svos', default=None)
nlp.add_pipe(pipeline_component, last=True)

class TestSVOs(unittest.TestCase):
    def setUp(self):
        pipeline_component.adj_as_object = False

    def test_svos_conjuction(self):        
        doc = nlp("making $12 an hour? where am i going to go? i have no other financial assistance available and he certainly won't provide support.")
        self.assertEqual(set(doc._.svos), {('i', 'not have', 'assistance'), ('he', 'wo not provide', 'support')})
        
    def test_svos_negation(self):
        doc = nlp("i don't have other assistance")
        assert set(doc._.svos) == {('i', 'do not have', 'assistance')}

    def test_svos(self):
        doc = nlp("They ate the pizza with anchovies.")
        assert set(doc._.svos) == {('they', 'ate', 'pizza')}

    def test_svos_conjunction_negation(self):
        doc = nlp("I have no other financial assistance available and he certainly won't provide support.")
        assert set(doc._.svos) == {('i', 'not have', 'assistance'), ('he', 'not provide', 'support')}

    def test_svos_simple_negation(self):
        doc = nlp("he did not kill me")
        assert set(doc._.svos) == {('he', 'did not kill', 'me')}

    def test_svos_distribution(self):
        doc = nlp("he is an evil man that hurt my child and sister")
        assert set(doc._.svos) == {('he', 'is', 'man'), ('man', 'hurt', 'child'), ('man', 'hurt', 'sister')}

    def test_svos_noun_phrase(self):
        pipeline_component.adj_as_object = True
        doc = nlp("he told me i would die alone with nothing but my career someday")
        assert set(doc._.svos) == {('he', 'told', 'me'), ('i', 'would die', 'alone'), ('i', 'would die', 'with nothing')}        

    def test_svos_want(self):
        doc = nlp("I wanted to kill him with a hammer.")
        assert set(doc._.svos) == {('i', 'wanted', 'to kill him')} 

    def test_svos(self):
        doc = nlp("because he hit me and also made me so angry i wanted to kill him with a hammer.")
        assert set(doc._.svos) == {('he', 'hit', 'me'), ('i', 'wanted','to kill him')}

    def test_svos_conjunction_distribution(self):
        doc = nlp("he and his brother shot me")
        # assert set(doc._.svos) == {('he', 'shot', 'me'), ('brother', 'shot', 'me')}

    def test_svos_distribution_conjunction(self):        
        doc = nlp("he and his brother shot me and my sister")
        assert set(doc._.svos) == {('he', 'shot', 'me'), ('he', 'shot', 'my sister'), ('his brother', 'shot', 'me'), ('his brother', 'shot', 'my sister')}

    def test_svos_indirect(self):
        doc = nlp("the annoying person that was my boyfriend hit me")
        assert set(doc._.svos) == {('person', 'was', 'boyfriend'), ('person', 'hit', 'me')}

    def test_svos_conjunction_negation(self):
        doc = nlp("the boy raced the girl who had a hat that had spots.")
        assert set(doc._.svos) == {('boy', 'raced', 'girl'), ('who', 'had', 'hat'), ('hat', 'had', 'spots')}

    def test_svos_preposition(self):
        doc = nlp("he spit on me")
        assert set(doc._.svos) == {('he', 'spit', 'on me')}

    def test_svos_negation_preposition(self):
        doc = nlp("he didn't spit on me")
        assert set(doc._.svos) == {('he', 'did not spit', 'on me')}

    def test_svos_preposition_negation(self):
        doc = nlp("the boy raced the girl who had a hat that didn't have spots.")
        assert set(doc._.svos) == {('boy', 'raced', 'girl'), ('who', 'had', 'hat'), ('hat', 'did not have', 'spots')}

    def test_svos_negation_conjuction_distribution(self):
        doc = nlp("he is a nice man that didn't hurt my child and sister")
        assert set(doc._.svos) == {('he', 'is', 'man'), ('man', 'did not hurt', 'child'), ('man', 'did not hurt', 'sister')}

    def test_svos_negation_prepostion_conjunction_distribution(self):
        doc = nlp("he didn't spit on me and my child")
        assert set(doc._.svos) == {('he', 'did not spit', 'on me'), ('he', 'did not spit', 'on child')}

    def test_svos_verb_conjunction(self):        
        doc = nlp("he beat and hurt me")
        assert set(doc._.svos) == {('he', 'beat', 'me'), ('he', 'hurt', 'me')}

    def test_svos_aux(self):
        pipeline_component.adj_as_object = True
        doc = nlp('The car is red.')
        assert set(doc._.svos) == {('car','is','red')}

if __name__ == '__main__':
    unittest.main()