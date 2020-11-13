# script to clean data, parse data and indexing in the 
import numpy as np
import pandas as pd
import json
import glob
import os
import pprint
import re
from bs4 import BeautifulSoup 
import logging

from haystack.preprocessor.utils import convert_files_to_dicts
from haystack.utils import print_answers
from haystack.document_store.elasticsearch import ElasticsearchDocumentStore
from haystack.retriever.sparse import ElasticsearchRetriever

DB_HOST = os.getenv("DB_HOST", "localhost")
document_store = ElasticsearchDocumentStore(host=DB_HOST, username="", password="", index="document")
document_store.delete_all_documents(index = 'document')

# Elesier dataset with full text
def nf2020toDict():
    paths = "./data/HACKXML0000000004/**/*.xml"
    target_tags = ['simple-para', 'para']

    docs = []
    for path in glob.glob(paths)[1:]:
        with open(path, 'r') as f: 
            data = BeautifulSoup(f.read() , "xml") 
        temp = {}
        temp["meta"] = {}
        temp["meta"]['title'] = data.find('title').getText()
        temp["meta"]["paper_id"] = data.find('aid').getText()
        temp["meta"]["doi"] = data.find('doi').getText()
        temp["meta"]["jid"] = data.find('jid').getText()
        
        paper_text = [t for t in data.find_all(text=True) if t.parent.name in target_tags]
        temp["text"] = ''.join(paper_text)
        
        docs.append(temp)
    return docs

nf_docs = nf2020toDict()
logging.info("Indexing Elesier articals with full text")
document_store.write_documents(nf_docs)


# Elesier dataset only with abstract
ctf_hackathon_doc = pd.read_json('./data/ctf-hackathon-upload.json', lines=True)

with open('./data/HACKXML0000000004/dataset.xml', 'r') as f: 
    papers_info = f.read() 
papers_info_data = BeautifulSoup(papers_info, "xml") 
paper_xml_doi_ls = np.unique([t.getText() for t in papers_info_data.find_all('doi')])
other_nfpaper_docs = ctf_hackathon_doc[~ctf_hackathon_doc.doi.isin(paper_xml_doi_ls)].copy()

other_nfpaper_docs_dicts = []
for i, row in other_nfpaper_docs.iterrows():
    temp = {}
    if isinstance(row['abstract'], str):
        temp['text'] = row['abstract']
        temp['meta'] = {}
        temp['meta']['title'] = row['title']
        temp['meta']['doi'] = row['doi'] if isinstance(row['doi'], str) else ''
        #temp['meta']['References'] = ', '.join(row['References']) if isinstance(row['References'], list) else ''
        temp['meta']['keywords'] = ' '.join(row['keywords']) if isinstance(row['keywords'], list) and len(row['keywords'])>0 else ''
        other_nfpaper_docs_dicts.append(temp)

logging.info("Indexing Elesier articals only with abstracts")
document_store.write_documents(other_nfpaper_docs_dicts)


# Compiled informatics PDF docs from the NF Registry website
pdf_dicts = convert_files_to_dicts(dir_path='./data/nf_info_pdfs/', split_paragraphs=True)
for p in pdf_dicts:
    p['text'] = re.sub(r'For more information on.*', '', ' '.join(p['text'].split('\n')))
pdf_docs = [p for p in pdf_dicts if not p['text'].startswith('Help end NF by joining the confidential NF Registry') and len(p['text'])>50]

logging.info("Indexing NF Registry PDF files")
document_store.write_documents(pdf_docs)


# PMC Articles
pmc_papers = pd.read_csv("./data/pmc_papers.csv")
pmc_papers['authors'] = pmc_papers['authors'].map(lambda x: ', '.join(x.split(','))+' et al' if isinstance(x, str) and len(x.split(','))>3 else x)

pmc_papers_docs_dicts = []
for i, row in pmc_papers.iterrows():
    temp = {}
    if isinstance(row['abstract'], str):
        temp['text'] = row['abstract']
        temp['meta'] = {}
        temp['meta']['title'] = row['title']
        temp['meta']['authors'] = row['authors'] if isinstance(row['authors'], str) else ''
        #temp['meta']['affliations'] = row['affliations'] if isinstance(row['affliations'], str) else ''
        temp['meta']['pmc_id'] = row['pmc_id']
        temp['meta']['keywords'] = row['keywords'] if isinstance(row['keywords'], str) else ''
        pmc_papers_docs_dicts.append(temp)
        
logging.info("Indexing PMC articles")    
document_store.write_documents(pmc_papers_docs_dicts)