import streamlit as st

from langchain_helper import get_qa_chain, create_vector_db

st.set_page_config(
    page_title="Customer Service Chatbot",
    page_icon="🤖"
)

st.title("CUSTOMER SERVICE CHATBOT 🤖")


# Create Knowledgebase
if st.button("Create Knowledgebase"):

    with st.spinner("Creating knowledgebase..."):

        try:
            create_vector_db()

            st.success(
                "Knowledgebase created successfully!"
            )

        except Exception as e:
            st.error(f"Error: {e}")


# Question
question = st.text_input(
    "Question:",
    placeholder="Ask your question here..."
)


if question:

    try:

        with st.spinner("Thinking..."):

            chain = get_qa_chain()

            response = chain.invoke({
                "query": question
            })

        st.header("Answer")

        st.write(response["result"])

    except Exception as e:

        st.error(f"Error: {e}")
