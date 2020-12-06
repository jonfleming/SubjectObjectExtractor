import spacy
from spacy.tokens import Doc
from SubjectObjectExtractor import SubjectObjectExtractor

nlp = spacy.load("en_core_web_md")
pipeline_component = SubjectObjectExtractor(nlp)
pipeline_component.adj_as_object = True
Doc.set_extension('svos', default=None)
nlp.add_pipe(pipeline_component, last=True)

file = open('test_text.txt', 'r')
i = 1
for line in file:
    print(i, line, end='')
    if not line.startswith('#'):
        doc = nlp(line)
        for svo in doc._.svos:
            print('    ', svo)
    i += 1
