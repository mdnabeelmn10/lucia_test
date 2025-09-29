import os
import json
import pandas as pd
import openai
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions
from ..models import Donation,UserRole
from django.contrib.auth import get_user_model

User = get_user_model()
openai.api_key = os.getenv("OPENAI_API_KEY")


SAFE_PANDAS_METHODS = [
    "head", "tail", "groupby", "sum", "count", "mean", "sort_values"
]

def generate_pandas_code(user_query: str, df_sample: pd.DataFrame):
    """
    Ask LLM to generate Pandas code for the user query.
    """
    columns = df_sample.columns.tolist()
    prompt = f"""
You are a Python expert. I have a Pandas DataFrame called 'df' with columns: {columns}.
Here are 5 sample rows:
{df_sample.head(5).to_dict(orient='records')}

Write Python code to answer this user query:
"{user_query}"

Rules:
- Incase you get a generic question give generic answer.
- Only use df and Pandas methods.
- Assign the final answer to variable 'result'.
- Do not access filesystem, OS, or any external data.
- Return only code, no explanation.
- I dont want you to mark the language such as python, Your output should just be something like result = df.loc[df['amount'].idxmax()]

"""
    resp = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=512
    )
    code = resp.choices[0].message["content"]
    print(code)
    return code

def execute_safe_pandas(code: str, df: pd.DataFrame):
    """
    Execute the code in a restricted namespace.
    """
    safe_globals = {"df": df, "result": None, "pd": pd}
    # very basic check for unsafe code
    forbidden = ["import", "open(", "os.", "sys.", "__"]
    if any(f in code for f in forbidden):
        raise ValueError("Unsafe code detected from LLM")
    exec(code, safe_globals)

    result = safe_globals.get("result")
    if isinstance(result, pd.DataFrame):
        result_data = result.to_dict(orient="records")
    elif isinstance(result, pd.Series):
        result_data = result.to_dict()
    else:
        result_data = result

    return result_data


def summarize(query,code_output):
    prompt = f'''You are a chatbot. Here's the query from user {query} and this is the answer from my dataset {code_output}.
      Can you summarize the result related to the question and avoid fields such as id and all which maybe unwanted. The code output or the answer from my dataset is of key importance
      Rules:
      - If the the answer is a data frame or a series summarize it in detail for each.
      - The amount is in dollars so ive appropriate sign.
      - Always give output as a string. 
      - Give to the point outputs.
      - Such as if input is hi give output as Hello! How can I assist you today? only.
      - Dont add any notes.
      - Also try giving proper line breaks as well so that it looks neat on frontend.'''
    resp = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=512
    )
    res = resp.choices[0].message["content"]
    return res

class NLQueryPandasAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        query = request.data.get("query")
        if not query:
            return Response({"error": "query is required"}, status=400)

        # Step 1: Get a manageable dataset for this user
        if user.role != UserRole.DONOR_ADVISOR:
            qs = Donation.objects.order_by("-date_recommended")[:500]
        else:
            qs = Donation.objects.filter(recommending_user=user).order_by("-date_recommended")[:500]

        if not qs.exists():
            return Response({"answer_text": "You have no donations yet.", "result": "No donations found."})

        # Step 2: Convert to Pandas
        df = pd.DataFrame(list(qs.values(
            "id", "recipient_charity__name", "recipient_charity__tin",
            "amount", "status", "date_recommended", "date_approved",
            "date_disbursed", "purpose", "is_anonymous", "is_recurring"
        )))
        df.rename(columns={
            "recipient_charity__name": "charity",
            "recipient_charity__tin": "charity_tin"
        }, inplace=True)
        df['amount'] = df['amount'].astype('float64')
        # Step 3: Ask LLM to generate Pandas code
        try:
            code = generate_pandas_code(query, df)
        except Exception as e:
            print(e)
            return Response({"error": f"LLM error: {str(e)}"}, status=500)

        # Step 4: Execute safely
        try:
            result = execute_safe_pandas(code, df)
        except Exception as e:
            print(e)
            return Response({"error": f"Execution error: {str(e)}"}, status=500)
        
        try:
            output = summarize(query,str(result))
        except Exception as e:
            print(e)
            return Response({"error": f"LLM error: {str(e)}"}, status=500)


        # Step 5: Return result
        return Response({
            "answer_text": f"Here is the result for your query: {output}",
            "result": output,
            "llm_code": code[:1000]  # optional: return only first 1000 chars
        })
