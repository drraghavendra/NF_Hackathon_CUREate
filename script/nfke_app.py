# to run the app: streamlit run streamlit_app.py
import streamlit as st
from annotated_text import annotated_text

import pandas as pd
import numpy as np
import pprint 
import os
import json
import requests 
import plotly.express as px

st.title('NF Knowledge Explorer')

CLINVAR_DATA = os.getenv('CLINVAR_DATA', "../data/nf_mutation_info.csv")
QA_MODEL_URL = os.getenv('QA_MODEL_URL', "http://127.0.0.1:8000/models/1/doc-qa")


@st.cache
def load_clinvar_data():
    clinvar_data = pd.read_csv(CLINVAR_DATA)
    return clinvar_data


@st.cache
def answer_question(question_txt):
    payload = {
      "questions": [
        question_txt
      ],
      "top_k_reader": 3,
      "top_k_retriever": 6
    }
    result = requests.post(QA_MODEL_URL, data=json.dumps(payload))
    if result.status_code == 200:
        prediction = json.loads(result.text)['results'][0]
        answers = get_answers(prediction)
        return answers
    else:
        return None

def get_answers(preds):
    all_answers = []
    for ap in preds['answers']:
        tmp = {}
        tmp['answer'] = ap.get('answer', '')
        tmp['context'] = ap.get('context', '')
        tmp['offset_start'] = ap.get('offset_start', 0)
        tmp['offset_end'] = ap.get('offset_end', 0)
        tmp['document_id'] = ap.get('document_id', '')
        meta_dict = ap.get('meta', None)
        if meta_dict:
            tmp['title'] = meta_dict.get('title', '')
            tmp['keywords'] = meta_dict.get('keywords', '')
        all_answers.append(tmp)
    #pprint.pprint(all_answers)
    return all_answers
    
def show_annotation_text(answers):
    paragraph = answers['context']
    start_idx = answers['offset_start']
    end_idx = answers['offset_end']
    return annotated_text('... ',
        paragraph[:start_idx],
        (paragraph[start_idx:end_idx], 'answer' ,"#faa"),
        paragraph[end_idx:], ' ...'
    )

data = load_clinvar_data()

if __name__ == "__main__":
    mutation_query = st.text_input("Search a Mutation:", "")
    question_query = st.text_input("Question:", "")
    
    if mutation_query!='':
        subset_data = data[data['Protein change'].str.contains(mutation_query, na=False)]
        st.subheader('Assosiated Diagnostics:')
        if subset_data.shape[0]>0:
            subset_data_symtoms_cnt = subset_data.groupby(['diagnosis', 'Clinical significance'])['Name'].count().reset_index().rename(columns={'Name':'count'})
            p = px.bar(subset_data_symtoms_cnt, x="diagnosis", y="count", color="Clinical significance")
            st.plotly_chart(p, use_container_width=True)
        else:
            st.warning(f"No relevant information is found associated with {mutation_query}")
        
        if st.checkbox('Show details'):
            st.subheader('Clinvar Mutation data')
            st.write(subset_data)
            
    if question_query!='':
        ans_prediction = answer_question(question_query)
        if ans_prediction:
            for ap in ans_prediction:
                title = ap.get('title',"")
                keywords = ap.get('keywords',"")
                show_keywords_str = f"**Keywords**: {keywords}" if keywords!='' else '' 
                st.markdown('**Title**: ' + title + '  \n' + show_keywords_str)
                show_annotation_text(ap)
            
        
        
