from flask import Flask, request, render_template_string, jsonify, render_template, url_for
from langchain_community.document_loaders import TextLoader
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings, OpenAI
from langchain.chains import RetrievalQA
from dotenv import load_dotenv
from datetime import datetime  # Add this with other imports
import os
import traceback
from charset_normalizer import from_path  # pip install charset-normalizer
from langchain_core.prompts import ChatPromptTemplate
import chardet
import tempfile
import magic  # python-magic-bin on Windows
from langchain_core.documents import Document
from werkzeug.utils import secure_filename
import os
from flask import Flask, request, render_template_string, jsonify, render_template, url_for, redirect  # Added redirect here





load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
app = Flask(__name__)




def detect_file_encoding(filepath):
    with open(filepath, 'rb') as f:
        raw_data = f.read(1024)  # Only check first 1KB for encoding
    return chardet.detect(raw_data)['encoding']

def is_file_binary(filepath):
    mime = magic.Magic(mime=True)
    file_type = mime.from_file(filepath)
    return 'text' not in file_type



# Initialize with a dummy document
embeddings = OpenAIEmbeddings(openai_api_key=api_key)



# Create strict prompt template
STRICT_PROMPT = ChatPromptTemplate.from_template(
    """Answer the question based only on the following context:
    {context}
    
    Question: {question}
    
    If you don't know the answer or the answer isn't in the context, 
    respond with "I don't know" or "This information is not in the provided documents".
    """
)





dummy_doc = Document(page_content="dummy", metadata={})
db = FAISS.from_documents([dummy_doc], embeddings)

# Remove the dummy document after initialization
db.delete([db.index_to_docstore_id[0]])  # Remove the first document

# Create QA chain
qa = RetrievalQA.from_chain_type(
    llm=OpenAI(openai_api_key=api_key),
    retriever=db.as_retriever(),
    chain_type_kwargs={"prompt": STRICT_PROMPT},
    return_source_documents=True 
)



@app.route('/')
def home():
    return render_template('index.html') 



@app.route('/ask_page')
def ask_page():
    return render_template('ask_page.html') 



# Configure upload folder
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'docx'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload', methods=['GET'])
def upload_page():
    return render_template('upload.html')




# Add this global variable (or use a database in production)
UPLOADED_FILES = []





@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file uploaded"}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "No selected file"}), 400
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            # Save the file first
            file.save(filepath)
            
            # Verify the file was saved
            if not os.path.exists(filepath):
                return jsonify({"error": "File failed to save"}), 500
            
            try:
                # Handle different file types
                if filename.endswith('.txt'):
                    # Read with encoding detection
                    with open(filepath, 'rb') as f:
                        raw_data = f.read()
                        result = from_path(filepath)
                        encoding = result.best().encoding if result else 'utf-8'
                    
                    # Create temporary properly encoded file
                    temp_path = os.path.join(app.config['UPLOAD_FOLDER'], f"temp_{filename}")
                    with open(temp_path, 'w', encoding=encoding) as f:
                        content = raw_data.decode(encoding, errors='replace')
                        
                        # ===== PREPROCESSING STARTS HERE =====
                        # 1. Remove any hidden special characters
                        content = ''.join(char for char in content if ord(char) < 128 or char.isspace())
                        
                        # 2. Normalize line endings
                        content = content.replace('\r\n', '\n').replace('\r', '\n')
                        
                        # 3. Remove excessive whitespace
                        content = '\n'.join(line.strip() for line in content.split('\n') if line.strip())
                        # ===== PREPROCESSING ENDS HERE =====
                        
                        f.write(content)
                    
                    loader = TextLoader(temp_path)
                
                elif filename.endswith('.pdf'):
                    from langchain_community.document_loaders import PyPDFLoader
                    loader = PyPDFLoader(filepath)
                
                elif filename.endswith('.docx'):
                    from langchain_community.document_loaders import Docx2txtLoader
                    loader = Docx2txtLoader(filepath)
                
                # Load and process documents
                docs = loader.load()
                
                # Additional document-level preprocessing
                for doc in docs:
                    # Remove any remaining special characters
                    doc.page_content = ''.join(char for char in doc.page_content if ord(char) < 128 or char.isspace())
                    # Normalize spaces
                    doc.page_content = ' '.join(doc.page_content.split())
                
                # Clean up temporary file if it exists
                if filename.endswith('.txt') and os.path.exists(temp_path):
                    os.remove(temp_path)
                
                # Verify we have valid content before adding to vector store
                if not docs or all(not doc.page_content.strip() for doc in docs):
                    raise ValueError("No readable content found after preprocessing")
                
                # Add to vector store
                global db
                db.add_documents(docs)
                
                # Only add to UPLOADED_FILES after successful processing
                file_info = {
                    "name": filename,
                    "size": f"{os.path.getsize(filepath) / 1024:.2f} KB",
                    "uploaded": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "pages": len(docs)
                }
                UPLOADED_FILES.append(file_info)
                
                return redirect(url_for('documents_page'))
                
            except Exception as load_error:
                # Clean up files if something went wrong
                if os.path.exists(filepath):
                    os.remove(filepath)
                if 'temp_path' in locals() and os.path.exists(temp_path):
                    os.remove(temp_path)
                
                return jsonify({
                    "error": "Failed to process file",
                    "message": str(load_error),
                    "details": "The file may be corrupted or in an unexpected format",
                    "advice": "Please try opening the file in a text editor and resaving it as plain text"
                }), 400
                
        else:
            return jsonify({
                "error": "Invalid file type",
                "allowed": "Only .txt, .pdf, and .docx files are accepted"
            }), 400
            
    except Exception as e:
        traceback.print_exc()
        return jsonify({
            "error": "Upload failed",
            "message": str(e),
            "advice": "Please check the file format and try again"
        }), 500




@app.route('/documents')
def documents_page():
    return render_template('documents.html', files=UPLOADED_FILES)




# Define greeting keywords
greetings = ["hello", "hi", "hey", "greetings", "good morning", "good afternoon", "good evening"]

@app.route("/ask", methods=["POST"])
def ask():
    try:
        query = request.form.get("user_query")
        if not query:
            return jsonify({"error": "No question provided"}), 400
        
        query_lower = query.lower().strip()

        # Respond to greetings directly
        if any(greet in query_lower for greet in greetings):
            return jsonify({
                "question": query,
                "answer": "Hello! How can I help you with the information in the document?",
                "sources": []
            })

        result = qa({"query": query})
        
        # Verify answer comes from documents
        if not result['source_documents']:
            return jsonify({
                "question": query,
                "answer": "This information is not in the provided documents.",
                "sources": []
            })

        return jsonify({
            "question": query,
            "answer": result['result'],
            "sources": [doc.metadata['source'] for doc in result['source_documents']]
        })

    except Exception as e:
        return jsonify({
            "error": "Error processing question",
            "details": str(e)
        }), 500




@app.route('/delete/<filename>', methods=['DELETE'])
def delete_file(filename):
    try:
        safe_filename = secure_filename(filename)
        if not safe_filename:
            return jsonify({"error": "Invalid filename"}), 400

        filepath = os.path.join(app.config['UPLOAD_FOLDER'], safe_filename)
        
        if not os.path.exists(filepath):
            return jsonify({"error": "File not found"}), 404

        # Remove from vector store
        removed_count = remove_document_from_vector_store(safe_filename)
        print(f"Removed {removed_count} document chunks from vector store")
        
        # Remove from UPLOADED_FILES list
        global UPLOADED_FILES
        UPLOADED_FILES = [f for f in UPLOADED_FILES if f['name'] != safe_filename]
        
        # Delete the physical file
        os.remove(filepath)
        
        return jsonify({
            "success": f"File '{safe_filename}' deleted",
            "removed_from_index": removed_count
        })
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# Add this function to your app.py
def remove_document_from_vector_store(filename):
    """Remove a document from the FAISS vector store"""
    global db
    
 
    # Get all documents
    all_docs = db.docstore._dict
    
    # Find documents with matching source (filename)
    docs_to_remove = []
    for doc_id, doc in all_docs.items():
        if doc.metadata.get('source', '').endswith(filename):
            docs_to_remove.append(doc_id)
    
    # Remove the documents
    if docs_to_remove:
        db.delete(docs_to_remove)
    
    return len(docs_to_remove)

# Run the app
if __name__ == "__main__":
    app.run(debug=True)
