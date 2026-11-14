# Lesson Title  
**Introduction to RAG (Retrieval-Augmented Generation)**  

---

## Learning Objectives  
- Understand what RAG means and why it is useful.  
- Learn the basic steps of how a RAG system works.  
- Identify the main components: document loading, chunking, embeddings, vector database, retrieval, augmented prompt, and generation.  
- Compare RAG with a plain LLM (Large Language Model).  
- Recognise the strengths and limits of RAG.  
- Avoid common beginner mistakes when building a RAG pipeline.  

---

## Introduction to AI  
Artificial Intelligence (AI) is a set of computer techniques that try to mimic human thinking.  
In everyday life, AI helps you get results when you type a query in **Google Search**, suggests replies in **WhatsApp**, or recommends videos on **YouTube**.  

A **Large Language Model (LLM)** is a type of AI that has read billions of words. It can write sentences, answer questions, and translate languages. However, an LLM only knows what it learned during its training. It cannot look up fresh information that was not in its training data.

---

## What is RAG?  
**RAG** stands for **Retrieval-Augmented Generation**.  
It is a method that **adds a "search step" before the LLM writes an answer**.  
The system first **retrieves** relevant pieces of text from a document collection, then **augments** the LLM’s prompt with those pieces, and finally asks the LLM to **generate** the final answer.

In short: *search -> add to prompt -> generate*.

---

## Why Do We Need RAG?  
LLM-only answers have two main problems:

| Problem | What it looks like | Why it matters |
|---------|-------------------|----------------|
| **Out-of-date knowledge** | The LLM may say "India’s Prime Minister is X" even after an election. | Users get wrong facts. |
| **Lack of domain-specific detail** | When asked about a college’s library policy, the LLM may guess. | Important decisions may be based on incorrect info. |

RAG solves these by letting the LLM **see up-to-date, trusted documents** at the moment of answering.

---

## How RAG Works — Step-by-Step  

1. **User asks a question** (e.g., "What is the library borrowing limit for students?").  
2. **Retriever** looks into a stored collection of documents and finds the most relevant pieces.  
3. Those pieces are **added to the prompt** that will be sent to the LLM.  
4. The LLM reads the prompt (question + retrieved text) and **writes a response**.  

All of this happens **at inference time** – i.e., when the user asks the question. The LLM’s internal weights are **never changed**.

---

## RAG Architecture Explained  

### 1. Document Loading  
- Gather all text you want the system to know (e.g., college handbook, news articles).  
- Store them in a folder or cloud bucket.

### 2. Text Chunking  
- Break each large document into **small pieces** called **chunks** (e.g., 200-300 words).  
- Small chunks are easier for the retriever to compare.

### 3. Embeddings  
- An **embedding** is a **list of numbers** that captures the meaning of a chunk.  
- Think of it as a "meaning fingerprint".  
- The same word or phrase will have similar numbers in different sentences.

### 4. Vector  
- A **vector** is simply that list of numbers (e.g., `[0.12, -0.34, 0.78, ...]`).  
- Vectors allow computers to measure how close two pieces of text are.

### 5. Vector Database  
- A **vector database** stores all the vectors (one per chunk).  
- It can quickly find vectors that are **closest** to a query vector.  
- Example products: Pinecone, Milvus, FAISS (open-source), ChromaDB.

### 6. Retrieval  
- When a user asks a question, the system creates an **embedding of the question**.  
- It then asks the vector database for the **top-k** most similar chunks.  
- **Top-k** means "the *k* most similar items". If *k = 3*, we get the three best matches.

### 7. Augmented Prompt  
- The original question is combined with the retrieved chunks.  
- This combined text is called the **augmented prompt**.  
- Example:  
  ```
  Question: What is the borrowing limit?  
  Context: "Undergraduate students may borrow up to 5 books for 30 days..."
  ```

### 8. Generation  
- The augmented prompt is sent to the LLM.  
- The LLM reads both the question and the context, then **generates** a final answer.  

**Important:** The LLM’s parameters stay the same. RAG only **adds information** at query time; it does **not** retrain or fine-tune the model.

---

## Practical Real-World Example  

### Example 1: College Library Help Desk (WhatsApp Bot)  
1. Load the college library handbook into the system.  
2. Chunk the handbook, embed each chunk, store in a vector DB.  
3. Student sends a WhatsApp message: "Can I renew a book online?"  
4. Retriever finds the relevant clause, adds it to the prompt.  
5. LLM replies: "Yes, you can renew a book online through the library portal up to two times before the due date."

### Example 2: News Fact-Checking Tool  
1. Collect recent news articles (last 7 days).  
2. Chunk, embed, store in vector DB.  
3. Journalist asks the tool: "Did the government announce a new tax on smartphones?"  
4. Retriever pulls the exact paragraph from a news article, passes it to the LLM.  
5. LLM answers: "Yes, on 10 Oct 2026 the government announced a 5% tax on smartphones, as reported by The Hindu."

Both examples show **no change to the LLM** – only the prompt is enriched with fresh documents.

---

## RAG vs. Traditional LLM  

| Aspect | Traditional LLM (no RAG) | RAG (Retrieval-Augmented Generation) |
|--------|--------------------------|--------------------------------------|
| **Source of knowledge** | Fixed at training time | Dynamic – can pull latest documents |
| **Handling of niche topics** | May guess or be vague | Retrieves exact relevant text |
| **Model updates** | Need full re-training to learn new facts | Only add new documents to the vector DB |
| **Computation cost** | One forward pass | Retrieval + one forward pass (slightly more) |
| **Risk of hallucination** | Higher (model may make up facts) | Lower – answer is grounded in retrieved text |

---

## Advantages of RAG  

- **Up-to-date information** without re-training the LLM.  
- **Domain specificity** – can focus on a particular subject (medicine, law, campus rules).  
- **Reduced hallucinations** because the LLM sees real text.  
- **Scalable** – add more documents, no need to change the LLM.  

---

## Limitations of RAG  

- **Quality of retrieved chunks** matters; bad chunks lead to bad answers.  
- **Latency** – searching the vector DB adds a small delay.  
- **Dependence on embedding quality** – poor embeddings reduce similarity matching.  
- **Prompt length limits** – only a limited number of chunks can fit into the LLM’s input window.  

---

## Common Beginner Mistakes  

| Mistake | Why it hurts | How to avoid |
|---------|--------------|--------------|
| **Thinking RAG changes the LLM** | Leads to wrong expectation of "learning". | Remember: RAG only **retrieves**, never **re-trains**. |
| **Using very large chunks** | Retrieval becomes less precise. | Keep chunks around 200-300 words. |
| **Forgetting to clean text** (e.g., HTML tags) | Embeddings capture noise. | Pre-process documents (remove headers, footers). |
| **Setting *k* too high** | Prompt exceeds LLM’s token limit. | Start with *k = 3-5* and adjust. |
| **Ignoring vector DB updates** | New documents are never searchable. | Re-embed and add new chunks whenever you add documents. |

---

## Key Takeaways  

- RAG = **Retrieval** + **Augmented Prompt** + **Generation**.  
- It **adds fresh, relevant text** to an LLM’s prompt at **inference time**.  
- No model weights are changed; the LLM stays the same.  
- Core pieces: document loading, chunking, embeddings, vector database, retrieval, augmented prompt, generation.  
- RAG improves accuracy and reduces hallucinations but needs good data handling and careful prompt design.  

---

## Glossary  

| Term | Simple Definition |
|------|-------------------|
| **RAG** | Retrieval-Augmented Generation – a method that first searches for relevant text and then asks a language model to write an answer using that text. |
| **LLM** | Large Language Model – a big AI model trained on lots of text to understand and generate language. |
| **Embedding** | A list of numbers that represents the meaning of a word, sentence, or chunk. |
| **Chunk** | A small piece of a larger document, usually a few sentences long. |
| **Vector** | The list of numbers (embedding) that can be compared with other vectors. |
| **Vector Database** | A storage system that holds vectors and can quickly find the ones most similar to a query vector. |
| **Retrieval** | The act of searching the vector database for the most similar chunks (often the **top-k**). |
| **Top-k** | The *k* most similar items returned by the retrieval step (e.g., top-3 = three best matches). |
| **Augmented Prompt** | The original user question plus the retrieved chunks, sent together to the LLM. |
| **Inference** | The moment when the model generates an answer for a new question (as opposed to training). |

---

## Multiple-Choice Questions  

1. **What does RAG add to an LLM’s prompt?**  
   - A) New model weights  
   - B) Retrieved document chunks  
   - C) Random numbers  
   - D) A different language  
   **Answer:** B) Retrieved document chunks  
   *Explanation:* RAG’s purpose is to retrieve relevant text and add it to the prompt; it does not modify the model itself.

2. **Which component stores the numeric representations of text?**  
   - A) Chunker  
   - B) Vector Database  
   - C) Tokenizer  
   - D) Decoder  
   **Answer:** B) Vector Database  
   *Explanation:* Vectors (embeddings) are saved in a vector database for fast similarity search.

3. **What does "top-k" mean in the retrieval step?**  
   - A) The first *k* characters of a document  
   - B) The *k* most similar chunks to the query  
   - C) The *k* longest sentences  
   - D) The *k* least relevant results  
   **Answer:** B) The *k* most similar chunks to the query  
   *Explanation:* "Top-k" selects the highest-scoring (most similar) items.

4. **Why is RAG useful for a college library chatbot?**  
   - A) It lets the bot learn new languages automatically.  
   - B) It lets the bot fetch the latest library rules without re-training.  
   - C) It reduces the size of the LLM.  
   - D) It removes the need for any documents.  
   **Answer:** B) It lets the bot fetch the latest library rules without re-training.  
   *Explanation:* The chatbot can retrieve current handbook sections at query time.

5. **Which of the following is NOT a limitation of RAG?**  
   - A) Retrieval latency  
   - B) Dependence on embedding quality  
   - C) Ability to change LLM weights on the fly  
   - D) Prompt length constraints  
   **Answer:** C) Ability to change LLM weights on the fly  
   *Explanation:* RAG never changes the LLM’s weights; this is a misconception.
