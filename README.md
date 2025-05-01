# rent-brigade-streamlit

## Setup

Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate
```

Install dependencies:
```bash
pip install -r requirements.txt
```

Create a `.streamlit` folder in the root directory and add the following file:
```bash
touch .streamlit/secrets.toml
```

Add SUPABASE_KEY to the `secrets.toml` file.


Run the app: 
```bash
streamlit run app.py
```



