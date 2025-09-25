# # donations/api/views.py
# import os
# import re
# import json
# import openai
# from datetime import datetime, timedelta
# from dateutil import parser as dateparser  # pip install python-dateutil
# from django.conf import settings
# from django.db.models import Sum, Count
# from rest_framework.views import APIView
# from rest_framework.response import Response
# from rest_framework import permissions 
# from ..permissions import IsLuciaAdmin, IsLuciaDirector, IsOwnerOfObject

# from ..models import Donation  # your Donation model from earlier
# from django.contrib.auth import get_user_model
# User = get_user_model()

# openai.api_key = os.getenv("OPENAI_API_KEY")  # ensure this is set in env

# # ---------- Helper: extract first JSON object robustly ----------
# def extract_first_json_object(text: str):
#     """
#     Finds first balanced {...} JSON object inside text and returns it.
#     Returns None if not found.
#     """
#     start = text.find("{")
#     if start == -1:
#         return None
#     stack = []
#     for i in range(start, len(text)):
#         ch = text[i]
#         if ch == "{":
#             stack.append(i)
#         elif ch == "}":
#             stack.pop()
#             if not stack:
#                 candidate = text[start:i+1]
#                 # Try to load json
#                 try:
#                     return json.loads(candidate)
#                 except json.JSONDecodeError:
#                     # try to fix trailing commas / simple problems by using regex cleanup
#                     try:
#                         clean = re.sub(r",\s*}", "}", candidate)
#                         clean = re.sub(r",\s*\]", "]", clean)
#                         return json.loads(clean)
#                     except Exception:
#                         return None
#     return None

# # ---------- Prompt & parser ----------
# SYSTEM_PROMPT = """
# You convert a user's natural language question about their own donations into a strict JSON object (AST)
# that our server will use to run safe Django ORM queries. **Return ONLY valid JSON (no explanation).**

# Rules:
# - Allowed "action" values:
#   - "count_donations"
#   - "sum_amount"
#   - "list_donations"
#   - "list_charities"
#   - "donations_by_charity" (grouped sums+counts)
#   - "latest_donations"
#   - "average_amount"
#   - "breakdown_by_status"
# - "filters" is a dictionary with optional keys:
#   - recipient_charity_name (string)
#   - recipient_charity_tin (string)
#   - source_daf_name (string)
#   - status (one of: pending_review, completed, rejected, approved)
#   - is_anonymous (true/false)
#   - is_recurring (true/false)
#   - date_from (ISO date "YYYY-MM-DD")
#   - date_to (ISO date "YYYY-MM-DD")
#   - date_field (one of: date_recommended, date_approved, date_disbursed) default date_recommended
#   - min_amount, max_amount (numbers)
# - Optional top-level keys:
#   - "limit" (integer, for lists)
#   - "order_by" (string, e.g., "-date_recommended" or "amount")
#   - "group_by" (string; only supported for donations_by_charity)
# - If the user asks relative ranges (e.g., "last year", "last 30 days", "this month"), compute exact ISO dates using current date = 2025-09-22 (Asia/Kolkata). Return date_from and date_to as ISO dates.
# - When uncertain about a filter, omit it rather than guessing.
# - ALWAYS output valid JSON, nothing else.
# """

# EXAMPLES = [
#     # Example 1
#     {
#         "nl": "How many donations have I made?",
#         "json": {"action": "count_donations", "filters": {}}
#     },
#     # Example 2
#     {
#         "nl": "What's the total amount I've donated to Red Cross in 2025?",
#         "json": {
#             "action": "sum_amount",
#             "filters": {
#                 "recipient_charity_name": "Red Cross",
#                 "date_from": "2025-01-01",
#                 "date_to": "2025-12-31"
#             }
#         }
#     },
#     # Example 3
#     {
#         "nl": "List my last 10 donations with details",
#         "json": {"action": "latest_donations", "limit": 10, "order_by": "-date_recommended"}
#     },
#     # Example 4
#     {
#         "nl": "Which charities I've donated to?",
#         "json": {"action": "list_charities", "filters": {}}
#     },
# ]


# def parse_nl_to_ast(user_query: str):
#     """
#     Call the LLM to convert natural language to a strict AST JSON (see SYSTEM_PROMPT).
#     Returns (ast_dict, llm_raw_text). If parsing fails, returns (None, raw_text).
#     """
#     # Compose messages with examples
#     system = SYSTEM_PROMPT
#     user_example_block = "Examples:\n"
#     for ex in EXAMPLES:
#         user_example_block += f"NL: {ex['nl']}\nJSON: {json.dumps(ex['json'])}\n\n"

#     messages = [
#         {"role": "system", "content": system},
#         {"role": "user", "content": user_example_block + f"Now convert this:\nNL: {user_query}\nJSON:"}
#     ]

#     try:
#         resp = openai.ChatCompletion.create(
#             model="gpt-4o-mini",  # change if needed
#             messages=messages,
#             temperature=0.0,
#             max_tokens=512
#         )
#     except Exception as e:
#         return None, f"LLM error: {str(e)}"

#     raw = resp.choices[0].message["content"]
#     ast = extract_first_json_object(raw)
#     return ast, raw

# # ---------- Fallback simple heuristics if LLM parsing fails ----------
# def heuristic_parse(user_query: str):
#     q = user_query.lower()
#     ast = {"action": None, "filters": {}}
#     if "how many" in q or "number of donations" in q or q.strip().startswith("count"):
#         ast["action"] = "count_donations"
#     elif "total" in q and ("donat" in q or "amount" in q):
#         ast["action"] = "sum_amount"
#     elif "what charities" in q or "which charities" in q or "charities i" in q:
#         ast["action"] = "list_charities"
#     elif "list" in q and "donations" in q or "show me all donations" in q:
#         ast["action"] = "list_donations"
#     elif "last" in q and "donation" in q:
#         ast["action"] = "latest_donations"
#         # try to extract number
#         m = re.search(r"last\s+(\d+)", q)
#         if m:
#             ast["limit"] = int(m.group(1))
#     else:
#         # default safe fallback: list last 10 donations
#         ast["action"] = "latest_donations"
#         ast["limit"] = 10
#     return ast

# # ---------- Build Django ORM filters safely ----------
# from django.db.models import Q

# def build_queryset_from_filters(user, filters: dict):
#     """
#     Returns a Django queryset filtered by 'filters'. Only uses ORM filter chaining (no raw SQL).
#     """
#     qs = Donation.objects.filter(recommending_user=user)
#     if not filters:
#         return qs

#     # charity name
#     c_name = filters.get("recipient_charity_name")
#     if c_name:
#         qs = qs.filter(recipient_charity__name__icontains=c_name)

#     tin = filters.get("recipient_charity_tin")
#     if tin:
#         qs = qs.filter(recipient_charity__tin__iexact=tin)

#     daf_name = filters.get("source_daf_name")
#     if daf_name:
#         qs = qs.filter(source_daf__name__icontains=daf_name)

#     status = filters.get("status")
#     if status:
#         qs = qs.filter(status=status)

#     if "is_anonymous" in filters:
#         qs = qs.filter(is_anonymous=bool(filters["is_anonymous"]))

#     if "is_recurring" in filters:
#         qs = qs.filter(is_recurring=bool(filters["is_recurring"]))

#     # amount filters
#     if "min_amount" in filters:
#         try:
#             qs = qs.filter(amount__gte=float(filters["min_amount"]))
#         except Exception:
#             pass
#     if "max_amount" in filters:
#         try:
#             qs = qs.filter(amount__lte=float(filters["max_amount"]))
#         except Exception:
#             pass

#     # date filtering
#     date_field = filters.get("date_field", "date_recommended")
#     df = filters.get("date_from")
#     dt = filters.get("date_to")
#     try:
#         if df:
#             df_dt = dateparser.parse(df)
#             qs = qs.filter(**{f"{date_field}__date__gte": df_dt.date()})
#         if dt:
#             dt_dt = dateparser.parse(dt)
#             qs = qs.filter(**{f"{date_field}__date__lte": dt_dt.date()})
#     except Exception:
#         # if parse fails, ignore date filters
#         pass

#     return qs

# # ---------- Execute AST safely using ORM ----------
# def execute_ast(ast: dict, user):
#     action = ast.get("action")
#     filters = ast.get("filters", {}) or {}
#     limit = ast.get("limit")
#     order_by = ast.get("order_by") or "-date_recommended"

#     qs = build_queryset_from_filters(user, filters)

#     if action == "count_donations":
#         count = qs.count()
#         return {"type": "count", "count": count, "text": f"You have made {count} donations."}

#     if action == "sum_amount":
#         total = qs.aggregate(total=Sum("amount"))["total"] or 0
#         return {"type": "sum", "total": float(total), "text": f"You have donated a total of {float(total):.2f}."}

#     if action == "average_amount":
#         total = qs.aggregate(total=Sum("amount"))["total"] or 0
#         cnt = qs.count()
#         avg = float(total / cnt) if cnt else 0.0
#         return {"type": "average", "average": avg, "text": f"Your average donation amount is {avg:.2f} across {cnt} donations."}

#     if action == "list_charities":
#         names = list(qs.values_list("recipient_charity__name", flat=True).distinct())
#         if not names:
#             return {"type": "list_charities", "charities": [], "text": "You haven't donated to any charities yet."}
#         return {"type": "list_charities", "charities": names, "text": "You have donated to: " + ", ".join(names)}

#     if action in ("list_donations", "latest_donations"):
#         if limit is None:
#             limit = ast.get("limit", 20)
#         # apply order and limit
#         rows = qs.order_by(order_by)[:limit]
#         data = []
#         for d in rows:
#             data.append({
#                 "id": str(d.id),
#                 "charity": d.recipient_charity.name if d.recipient_charity else None,
#                 "charity_tin": getattr(d.recipient_charity, "tin", None),
#                 "amount": float(d.amount),
#                 "status": d.status,
#                 "date_recommended": d.date_recommended.isoformat() if d.date_recommended else None,
#                 "date_approved": d.date_approved.isoformat() if d.date_approved else None,
#                 "date_disbursed": d.date_disbursed.isoformat() if d.date_disbursed else None,
#                 "purpose": d.purpose,
#                 "is_anonymous": d.is_anonymous,
#                 "is_recurring": d.is_recurring
#             })
#         text = f"Returning {len(data)} donation(s)."
#         return {"type": "list_donations", "donations": data, "text": text}

#     if action == "donations_by_charity":
#         grouped = qs.values("recipient_charity__name").annotate(total=Sum("amount"), count=Count("id")).order_by("-total")
#         data = [{"charity": g["recipient_charity__name"], "total_amount": float(g["total"] or 0), "count": int(g["count"])} for g in grouped]
#         return {"type": "donations_by_charity", "groups": data, "text": "Donations grouped by charity returned."}

#     if action == "breakdown_by_status":
#         grouped = qs.values("status").annotate(count=Count("id"), total=Sum("amount"))
#         data = [{"status": g["status"], "count": int(g["count"]), "total_amount": float(g["total"] or 0)} for g in grouped]
#         return {"type": "breakdown_by_status", "groups": data, "text": "Breakdown by status returned."}

#     # default fallback if action unknown
#     # return a summary to the user: count + total + top charities
#     total = qs.aggregate(total=Sum("amount"))["total"] or 0
#     count = qs.count()
#     top_charities = list(qs.values_list("recipient_charity__name", flat=True).distinct()[:10])
#     text = f"I couldn't determine a precise requested action. For your current filters: {count} donations, total {float(total):.2f}."
#     return {"type": "fallback_summary", "count": count, "total": float(total), "charities": top_charities, "text": text}


# # ---------- API View ----------
# class NLQueryAPIView(APIView):
#     """
#     POST { "query": "How many donations have i made?" }
#     Response: structured JSON with 'answer_text' and 'result' (structured data).
#     """
#     # permission_classes = [IsAuthenticatedOrReadOnly]
#     permission_classes = [permissions.IsAuthenticated]


#     def post(self, request):
#         user = request.user if request.user.is_authenticated else None
#         if user is None:
#             # allow testing via `user_id` param (not recommended in prod)
#             user_id = request.data.get("user_id")
#             if not user_id:
#                 return Response({"error": "Authentication required or provide user_id for testing."}, status=401)
#             try:
#                 user = User.objects.get(id=user_id)
#             except Exception:
#                 return Response({"error": "Invalid user_id"}, status=400)

#         query = request.data.get("query")
#         if not query:
#             return Response({"error": "query is required"}, status=400)

#         # 1) Parse NL to AST using LLM
#         ast, llm_raw = parse_nl_to_ast(query)

#         # 2) If LLM failed to return ast, use heuristics
#         used_fallback = False
#         if ast is None:
#             ast = heuristic_parse(query)
#             used_fallback = True

#         # 3) Execute AST safely
#         try:
#             result = execute_ast(ast, user)
#         except Exception as e:
#             # if anything goes wrong in ORM execution, gracefully fallback to heuristic summary
#             ast = heuristic_parse(query)
#             result = execute_ast(ast, user)
#             result["warning"] = f"Encountered error while executing AST: {str(e)} (used heuristic fallback)"

#         # 4) Return data + debug info (limited)
#         response = {
#             "answer_text": result.get("text"),
#             "result": result,
#             "ast": ast,
#             "llm_raw": llm_raw if not used_fallback else None,
#             "used_fallback_parser": used_fallback
#         }
#         print(response)
#         return Response(response)


# donations/api/views.py
import os
import json
import pandas as pd
import openai
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions
from ..models import Donation
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
        qs = Donation.objects.filter(recommending_user=user).order_by("-date_recommended")[:500]
        if not qs.exists():
            return Response({"answer_text": "You have no donations yet.", "result": {}})

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
