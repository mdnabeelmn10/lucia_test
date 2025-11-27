# import uuid
# import requests, re
# from bs4 import BeautifulSoup
# import json
# from urllib.parse import urljoin, urlparse
# import os
# from difflib import SequenceMatcher

# from rest_framework.decorators import api_view, permission_classes
# from rest_framework.response import Response
# from rest_framework import status,permissions

# from ..models import Charity
# from ..serializers import CharitySerializer
# from ..permissions import IsLuciaAdmin, IsLuciaDirector
# from django.db.models import Q


# from openai import OpenAI

# client = OpenAI()

# SERP_API_KEY = os.getenv("SERP_API_KEY")

# def _get_context_from_session(request):
#     """Retrieve previous charity chat context from session."""
#     history = request.session.get("ai_charity_context", [])
#     return "\n".join(history[-3:])  


# def _update_context_session(request, user_input, ai_output):
#     """Store last few user ↔ AI messages for conversational continuity."""
#     history = request.session.get("ai_charity_context", [])
#     history.append(f"User: {user_input}\nAI: {ai_output}")
#     request.session["ai_charity_context"] = history[-5:] 

# def get_charity_contact_info(charity_name,address):
#     serp_url = "https://serpapi.com/search.json"
#     params = {
#         "engine": "google",
#         "q": f"{charity_name} official site in {address}",
#         "api_key": SERP_API_KEY
#     }

#     try:
#         res = requests.get(serp_url, params=params, timeout=10)
#         data = res.json()
#         website = None
#         if "organic_results" in data and len(data["organic_results"]) > 0:
#             website = data["organic_results"][0].get("link", None)
#     except Exception as e:
#         print(f"Google search failed for {charity_name}: {e}")
#         return {"website": None, "emails": [], "phones": []}

#     if not website:
#         print(f"No website found for {charity_name}")
#         return {"website": None, "emails": [], "phones": []}

#     def scrape_page(url):
#         try:
#             html = requests.get(url, timeout=10).text
#             # emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(?<!\.\d{1,3})',html)
#             emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[A-Za-z]{2,}',html)
#             phones = re.findall(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', html)
#             emails = list(set([e for e in emails if not e.endswith((".png", ".jpg", ".jpeg","1","2","3","4","5","6","7","8","9","0"))]))
#             phones = list(set(phones))
#             return emails, phones, html
#         except Exception as e:
#             print(f"Error scraping {url}: {e}")
#             return [], [], ""

#     all_emails, all_phones, html = scrape_page(website)
#     soup = BeautifulSoup(html, "html.parser")

#     contact_links = []
#     for link in soup.find_all("a", href=True):
#         href = link["href"].lower()
#         if any(k in href for k in ["contact", "about", "team", "staff"]):
#             full_url = urljoin(website, href)
#             domain = urlparse(full_url).netloc
#             if domain == urlparse(website).netloc:
#                 contact_links.append(full_url)
#     contact_links = list(set(contact_links))

#     for link in contact_links:
#         sub_emails, sub_phones, _ = scrape_page(link)
#         all_emails.extend(sub_emails)
#         all_phones.extend(sub_phones)

#     all_emails = list(set(all_emails))
#     all_phones = list(set(all_phones))

#     final = {"website": website, "emails": all_emails, "phones": all_phones}
#     # print(final)
#     return final

# @api_view(["POST"])
# @permission_classes([permissions.AllowAny])
# def search_and_update_charity(request):
#     print("[LOOKUP]", request.data)
#     charity_name = (request.data.get("charity_name") or "").strip()
#     tin = (request.data.get("tin") or "").strip()

#     if not charity_name and not tin:
#         return Response({"error": "Either charity_name or tin is required."},
#                         status=status.HTTP_400_BAD_REQUEST)

#     if tin and not charity_name:
#         charity = Charity.objects.filter(tin__iexact=tin).first()
#         if charity:
#             serializer = CharitySerializer(charity)
#             print(f"[FAST EIN LOOKUP] Found: {charity.name}")
#             return Response({
#                 "source": "database",
#                 "message": "Found charity by EIN (no enrichment needed).",
#                 "matches": [serializer.data],
#                 "needs_clarification": False,
#                 "enrichment_done": False,
#                 "via": "database"
#             }, status=200)
#         else:
#             print(f"[FAST EIN LOOKUP] No match for EIN {tin}")
#             return Response({"error": "No match for EIN."}, status=404)

#     filters = Q()
#     if charity_name:
#         filters |= Q(name__icontains=charity_name)
#     if tin:
#         filters |= Q(tin__iexact=tin)

#     matches = Charity.objects.filter(filters).distinct()
#     if not matches.exists():
#         return Response({"error": "Charity not found in local database. Only enrichment allowed."},
#                         status=status.HTTP_404_NOT_FOUND)

#     def name_similarity(a, b):
#         try:
#             return SequenceMatcher(None, a.lower(), b.lower()).ratio()
#         except Exception:
#             return 0.0

#     sorted_matches = sorted(matches, key=lambda c: name_similarity(charity_name, c.name), reverse=True)
#     matches = sorted_matches

#     MAX_ENRICH = 5
#     enriched = []
#     any_updated = False

#     for idx, charity in enumerate(matches):
#         contact_missing = (
#             not charity.website and not charity.contact_email and not charity.contact_telephone
#         )

#         if contact_missing and idx < MAX_ENRICH:
#             info = get_charity_contact_info(charity.name,charity.address)
#             updated = False
#             if info.get("website"):
#                 charity.website = info["website"]
#                 updated = True
#             if info.get("emails"):
#                 charity.contact_email = info["emails"][0]
#                 updated = True
#             if info.get("phones"):
#                 charity.contact_telephone = info["phones"][0]
#                 updated = True

#             if updated:
#                 charity.save()
#                 any_updated = True
#                 print(f"[Enriched] {charity.name}")

#         enriched.append(CharitySerializer(charity).data)

#     if len(enriched) == 1:
#         return Response({
#             "source": "database",
#             "message": "Single charity record found.",
#             "matches": enriched,
#             "needs_clarification": False,
#             "enrichment_done": any_updated
#         }, status=200)

#     return Response({
#         "source": "database",
#         "message": f"Multiple charities found. Showing top {len(enriched)} and enriched top {MAX_ENRICH}.",
#         "matches": enriched,
#         "needs_clarification": True,
#         "enrichment_done": any_updated
#     }, status=200)

# @api_view(["POST"])
# @permission_classes([permissions.AllowAny])
# def ai_search_charity(request):
#     print("[AI SEARCH]", request.data)
#     name = (request.data.get("charity_name") or request.data.get("name") or "").strip()
#     tin = (request.data.get("tin") or "").strip()

#     if not name and not tin:
#         return Response({"error": "charity_name or EIN required"}, status=status.HTTP_400_BAD_REQUEST)

#     previous_context = _get_context_from_session(request)
#     user_input = name or tin

#     if tin:
#         charity = Charity.objects.filter(tin__iexact=tin).first()
#         if charity:
#             serializer = CharitySerializer(charity)
#             ai_output = f"Found {charity.name} by EIN."
#             _update_context_session(request, user_input, ai_output)
#             return Response({
#                 "source": "database",
#                 "message": "Found charity by EIN (no enrichment needed).",
#                 "matches": [serializer.data],
#                 "needs_clarification": False,
#                 "enrichment_done": False,
#                 "via": "database"
#             }, status=status.HTTP_200_OK)
#         else:
#             print(f"[FAST EIN LOOKUP] No match for EIN {tin}")
#             return _search_with_openai(f'EIN (TIN) "{tin}"', previous_context)

#     from django.test import Client
#     test_client = Client()
#     lookup_payload = {"charity_name": name, "tin": tin}
#     internal_res = test_client.post(
#         "/lookup/",
#         data=json.dumps(lookup_payload),
#         content_type="application/json"
#     )

#     if internal_res.status_code == 200:
#         payload = internal_res.json()
#         payload["via"] = "database"
#         _update_context_session(request, user_input, "Found in internal DB.")
#         return Response(payload, status=200)

#     result = _search_with_openai(f'name "{name}"', previous_context)
#     _update_context_session(request, user_input, str(result.data))
#     return result

# # @api_view(["POST"])
# # @permission_classes([permissions.AllowAny])
# # def ai_search_charity(request):
# #     print("[AI SEARCH]", request.data)
# #     name = (request.data.get("charity_name") or request.data.get("name") or "").strip()
# #     tin = (request.data.get("tin") or "").strip()

# #     if not name and not tin:
# #         return Response({"error": "charity_name or EIN required"}, status=400)

# #     if tin:
# #         charity = Charity.objects.filter(tin__iexact=tin).first()
# #         if charity:
# #             serializer = CharitySerializer(charity)
# #             print(f"[FAST EIN LOOKUP] Found: {charity.name}")
# #             return Response({
# #                 "source": "database",
# #                 "message": "Found charity by EIN (no enrichment needed).",
# #                 "matches": [serializer.data],
# #                 "needs_clarification": False,
# #                 "enrichment_done": False,
# #                 "via": "database"
# #             }, status=200)
# #         else:
# #             print(f"[FAST EIN LOOKUP] No match for EIN {tin}")
# #             return _search_with_openai(f'EIN (TIN) "{tin}"')

# #     from django.test import Client
# #     test_client = Client()
# #     lookup_payload = {"charity_name": name, "tin": tin}
# #     internal_res = test_client.post(
# #         "/lookup/",
# #         data=json.dumps(lookup_payload),
# #         content_type="application/json"
# #     )

# #     if internal_res.status_code == 200:
# #         payload = internal_res.json()
# #         payload["via"] = "database"
# #         return Response(payload, status=200)

# #     descriptor = f'name "{name}"' if name else f'EIN "{tin}"'
# #     return _search_with_openai(descriptor)

# def _search_with_openai(search_descriptor: str, previous_context=None):
#     """
#     Uses GPT-4o-mini with web search to retrieve verified US charity data.
#     Searches only candid.org, charitynavigator.org, and IRS.gov.
#     """
#     context_text = f"\nPrevious context:\n{previous_context}\n" if previous_context else ""

#     prompt = f"""
# You are a US charity verification assistant.
# The user searched for {search_descriptor}.

# Your job:
# - Search online ONLY on verified domains:
#   * candid.org (Guidestar)
#   * charitynavigator.org
#   * apps.irs.gov
# - Return only verified US charities (nonprofits, churches, schools, NGOs).
# - EIN (TIN) must come from the source; do NOT fabricate it.
# - If nothing verified found, respond with empty matches and needs_clarification=true.

# Return ONLY JSON:
# {{
#   "matches": [
#     {{
#       "name": "",
#       "location": "",
#       "type": "",
#       "website": "",
#       "address": "",
#       "contact_email": "",
#       "contact_phone": "",
#       "tin": "",
#       "confidence": 0.0
#     }}
#   ],
#   "needs_clarification": true|false,
#   "explanation": "brief explanation of what was found"
# }}
# {context_text}
# """

#     try:
#         completion = client.chat.completions.create(
#             model="gpt-4o-mini",
#             temperature=0.2,
#             messages=[
#                 {"role": "system", "content": "You are a trusted US charity verification assistant who only uses verified web sources."},
#                 {"role": "user", "content": prompt}
#             ],
#             # tools=[{"type": "web_search"}],
#             response_format={"type": "json_object"},
#             timeout=25
#         )

#         raw = completion.choices[0].message.content
#         result_json = json.loads(raw) if isinstance(raw, str) else raw

#     except Exception as e:
#         print(f"[OpenAI Error] {e}")
#         return Response({"via": "openai", "error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#     matches = [m for m in result_json.get("matches", []) if m.get("tin")]

#     if not matches:
#         return Response({
#             "via": "openai",
#             "results": {
#                 "matches": [],
#                 "needs_clarification": True,
#                 "explanation": result_json.get("explanation", "No verified US-based charities found.")
#             }
#         }, status=200)

#     # Sort by location and confidence
#     matches.sort(key=lambda m: (m.get("location", "").lower(), -m.get("confidence", 0)))

#     return Response({
#         "via": "openai",
#         "results": {
#             "matches": matches,
#             "needs_clarification": result_json.get("needs_clarification", False),
#             "explanation": result_json.get("explanation", "")
#         }
#     }, status=200)

# # def _search_with_openai(search_descriptor: str):
# #     prompt = f"""
# # You are an assistant that helps identify verified US-based organizations (charities, colleges, churches).
# # The user searched using {search_descriptor}.
# # You must only return organizations based in the United States.

# # Return ONLY JSON:
# # {{
# #   "matches": [
# #     {{
# #       "name": "",
# #       "location": "",
# #       "type": "",
# #       "website": "",
# #       "address": "",
# #       "contact_email": "",
# #       "contact_phone": "",
# #       "tin": "",
# #       "confidence": 0.0
# #     }}
# #   ],
# #   "needs_clarification": true|false,
# #   "explanation": "brief explanation"
# # }}

# # Rules:
# # - Only return US-based entities.
# # - Do not include non-US organizations.
# # - EIN (tin) is mandatory for every match. If EIN is not found, omit that match entirely.
# # """

# #     try:
# #         completion = client.chat.completions.create(
# #             model="gpt-4o-mini",
# #             messages=[{"role": "user", "content": prompt}],
# #             response_format={"type": "json_object"},
# #             timeout=10
# #         )
# #         raw = completion.choices[0].message.content
# #         result_json = json.loads(raw) if isinstance(raw, str) else raw
# #     except Exception as e:
# #         print(f"[OpenAI Error] {e}")
# #         return Response({"via": "openai", "error": str(e)}, status=500)

# #     matches = [m for m in result_json.get("matches", []) if m.get("tin")]

# #     if not matches:
# #         return Response({
# #             "via": "openai",
# #             "results": {
# #                 "matches": [],
# #                 "needs_clarification": False,
# #                 "explanation": "No valid US-based matches with EIN found."
# #             }
# #         }, status=200)

# #     return Response({
# #         "via": "openai",
# #         "results": {
# #             "matches": matches,
# #             "needs_clarification": result_json.get("needs_clarification", False),
# #             "explanation": result_json.get("explanation", "")
# #         }
# #     }, status=200)


# from django.test.client import RequestFactory
# from django.contrib.sessions.middleware import SessionMiddleware
# from rest_framework.decorators import api_view, permission_classes
# from rest_framework.response import Response
# from rest_framework import permissions, status


# @api_view(["POST"])
# @permission_classes([permissions.AllowAny])
# def ai_router(request):
#     """
#     Unified AI endpoint that routes between charity search and conversation-based refinement.
#     Supports chat-like filtering (e.g., "the one in Toms River").
#     """
#     message = (request.data.get("message") or "").strip()
#     charity_name = (request.data.get("charity_name") or "").strip()
#     tin = (request.data.get("tin") or "").strip()
#     previous_context = (request.data.get("previous_context") or "").strip()
#     print(message,charity_name,tin,previous_context)
#     if not message:
#         return Response({"error": "message is required"}, status=status.HTTP_400_BAD_REQUEST)

#     # previous_context = _get_context_from_session(request)

#     # Detect if this is a search or clarification
#     search_keywords = ["find", "charity", "organization", "foundation", "ein", "lookup", "search", "ngo"]
#     is_search = any(kw in message.lower() for kw in search_keywords)

#     # 1️⃣ Handle SEARCH INTENT
#     if is_search or len(message.split()) <= 3:
#         print("[ROUTER] Detected SEARCH intent → /ai-search/")

#         # --- Create fake request with session ---
#         factory = RequestFactory()
#        # Detect if the message looks like an EIN/TIN (digits, possibly with dash)
#         is_tin = message.replace("-", "").isdigit() and (7 <= len(message.replace("-", "")) <= 9)

#         payload = {"charity_name": "", "tin": ""}
#         payload["tin"] = tin or ""
#         payload["charity_name"] = charity_name or ""

#         # if is_tin:
#         #     payload["tin"] = tin
#         # else:
#         #     payload["charity_name"] = charity_name

#         fake_req = factory.post(
#             "/ai-search/",
#             payload,
#             content_type="application/json",
#         )


#         # Attach a valid session so _get_context_from_session() works
#         middleware = SessionMiddleware(lambda r: None)
#         middleware.process_request(fake_req)
#         fake_req.session.save()

#         # ✅ Call the existing ai_search_charity view safely
#         result = ai_search_charity(fake_req)

#         # --- Store results for follow-up filtering ---
#         try:
#             matches = (
#                 result.data.get("results", {}).get("matches", [])
#                 if isinstance(result.data, dict)
#                 else []
#             )
#             if matches:
#                 request.session["ai_last_matches"] = matches
#                 request.session.modified = True
#                 print(f"[SESSION] Stored {len(matches)} results for refinement.")
#         except Exception as e:
#             print(f"[SESSION STORAGE ERROR] {e}")

#         return result

#     # 2️⃣ Handle FILTER or CLARIFICATION intent
#     print("[ROUTER] Detected FILTER or CLARIFICATION intent")
#     last_matches = request.session.get("ai_last_matches", [])

#     if last_matches:
#         filtered = _filter_results(last_matches, message)
#         print(filtered)
#         if filtered:
#             _update_context_session(request, message, f"Filtered {len(filtered)} results.")
#             return Response(
#                 {
#                     "via": "filter",
#                     "message": f"Filtered results based on '{message}'",
#                     "matches": filtered,
#                 },
#                 status=status.HTTP_200_OK,
#             )

#         # No local match — ask OpenAI to clarify
#         return _clarify_with_openai(message, previous_context, last_matches)

#     # 3️⃣ No previous results — direct clarification
#     return _clarify_with_openai(message, previous_context)

# def _filter_results(matches, message):
#     """
#     Filters charity matches based on address/city/state keywords in user message.
#     """
#     filtered = []
#     msg_lower = message.lower()

#     for m in matches:
#         addr = f"{m.get('address', '')} {m.get('location', '')}".lower()
#         if any(token in addr for token in msg_lower.split()):
#             filtered.append(m)

#     return filtered

# def _clarify_with_openai(message: str, previous_context=None, last_matches=None):
#     """
#     Uses GPT-4o-mini to clarify user's intent or discuss previous charity results.
#     """
#     context_text = f"\nPrevious context:\n{previous_context}\n" if previous_context else ""
#     match_text = ""
#     if last_matches:
#         top = "\n".join([f"- {m.get('name')} ({m.get('location', '')})" for m in last_matches[:5]])
#         match_text = f"\nRecent results:\n{top}\n"

#     prompt = f"""
# You are a helpful assistant for verified US charities.

# User said: "{message}"
# {context_text}
# {match_text}

# If the user mentions a location or state, filter the above results accordingly.
# If unsure, ask politely for clarification (e.g., "Do you mean the one in Toms River, NJ?").
# Never invent new charities.
# """

#     try:
#         completion = client.chat.completions.create(
#             model="gpt-4o-mini",
#             temperature=0.4,
#             messages=[
#                 {"role": "system", "content": "You are a factual assistant for verified US charity data."},
#                 {"role": "user", "content": prompt}
#             ],
#             timeout=15
#         )
#         reply = completion.choices[0].message.content
#         return Response({
#             "via": "openai-clarifier",
#             "reply": reply
#         }, status=200)
#     except Exception as e:
#         print(f"[OpenAI Clarifier Error] {e}")
#         return Response({"error": str(e)}, status=500)


import os
import re
import json
from difflib import SequenceMatcher
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt

from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status, permissions

from ..models import Charity
from ..serializers import CharitySerializer

from openai import OpenAI

client = OpenAI()
SERP_API_KEY = os.getenv("SERP_API_KEY")


# -----------------------------------------------------------------------------
# Session helpers
# -----------------------------------------------------------------------------

def _get_context_from_session(request):
    """Retrieve previous charity chat context from session."""
    history = request.session.get("ai_charity_context", [])
    return "\n".join(history[-3:])  # last few turns


def _update_context_session(request, user_input, ai_output):
    """Store last few user ↔ AI messages for conversational continuity."""
    history = request.session.get("ai_charity_context", [])
    history.append(f"User: {user_input}\nAI: {ai_output}")
    request.session["ai_charity_context"] = history[-5:]  # keep last 5


def _store_last_matches(request, matches):
    """Store last matches for later filtering."""
    if not matches:
        return
    request.session["ai_last_matches"] = matches
    request.session.modified = True


def _get_last_matches(request):
    return request.session.get("ai_last_matches", [])


# -----------------------------------------------------------------------------
# Optional enrichment via SERP + scraping (same as your original)
# -----------------------------------------------------------------------------

def get_charity_contact_info(charity_name, address):
    """
    Try to find website / email / phone for a charity using SERPAPI + scraping.
    Only used when DB record is missing contact info.
    """
    if not SERP_API_KEY:
        return {"website": None, "emails": [], "phones": []}

    serp_url = "https://serpapi.com/search.json"
    params = {
        "engine": "google",
        "q": f"{charity_name} official site in {address}",
        "api_key": SERP_API_KEY,
    }

    try:
        res = requests.get(serp_url, params=params, timeout=10)
        data = res.json()
        website = None
        if "organic_results" in data and len(data["organic_results"]) > 0:
            website = data["organic_results"][0].get("link", None)
    except Exception as e:
        print(f"[SERP ERROR] {charity_name}: {e}")
        return {"website": None, "emails": [], "phones": []}

    if not website:
        print(f"[SERP] No website found for {charity_name}")
        return {"website": None, "emails": [], "phones": []}

    def scrape_page(url):
        try:
            html = requests.get(url, timeout=10).text
            emails = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[A-Za-z]{2,}", html)
            phones = re.findall(r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", html)
            emails = list(
                set(
                    [
                        e
                        for e in emails
                        if not e.lower().endswith(
                            (".png", ".jpg", ".jpeg", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0")
                        )
                    ]
                )
            )
            phones = list(set(phones))
            return emails, phones, html
        except Exception as e:
            print(f"[SCRAPE ERROR] {url}: {e}")
            return [], [], ""

    all_emails, all_phones, html = scrape_page(website)
    soup = BeautifulSoup(html, "html.parser")

    contact_links = []
    for link in soup.find_all("a", href=True):
        href = link["href"].lower()
        if any(k in href for k in ["contact", "about", "team", "staff"]):
            full_url = urljoin(website, href)
            domain = urlparse(full_url).netloc
            if domain == urlparse(website).netloc:
                contact_links.append(full_url)
    contact_links = list(set(contact_links))

    for link in contact_links:
        sub_emails, sub_phones, _ = scrape_page(link)
        all_emails.extend(sub_emails)
        all_phones.extend(sub_phones)

    all_emails = list(set(all_emails))
    all_phones = list(set(all_phones))

    return {"website": website, "emails": all_emails, "phones": all_phones}


# -----------------------------------------------------------------------------
# OpenAI search helper (no web_search tool, JSON-only)
# -----------------------------------------------------------------------------

def _search_with_openai(search_descriptor: str, previous_context=None):
    """
    Uses GPT-4o-mini to identify verified US charities.
    No web_search tool; we just strongly instruct it not to hallucinate.
    Returns a plain dict; views wrap it in Response.
    """
    context_text = f"\nPrevious context:\n{previous_context}\n" if previous_context else ""

    prompt = f"""
You are a US charity verification assistant.
The user searched for {search_descriptor}.

Rules:
- Only return real US-based organizations (nonprofits, churches, schools, NGOs).
- EIN (TIN) must be an actual known EIN; if you are not sure, do NOT include that match.
- Never invent fake organizations, addresses, or EINs.
- If you are uncertain, return an empty matches list and set needs_clarification=true.

Return ONLY JSON:
{{
  "matches": [
    {{
      "name": "",
      "location": "",
      "type": "",
      "website": "",
      "address": "",
      "contact_email": "",
      "contact_phone": "",
      "tin": "",
      "confidence": 0.0
    }}
  ],
  "needs_clarification": true|false,
  "explanation": "brief explanation of what was found or why not"
}}
{context_text}
"""

    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.2,
            messages=[
                {
                    "role": "system",
                    "content": "You are a cautious assistant that NEVER fabricates charity data. If unsure, return no matches.",
                },
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            timeout=20,
        )
        raw = completion.choices[0].message.content
        result_json = json.loads(raw) if isinstance(raw, str) else raw
    except Exception as e:
        print(f"[OpenAI Error] {e}")
        return {
            "via": "openai",
            "error": str(e),
            "results": {
                "matches": [],
                "needs_clarification": True,
                "explanation": "Error contacting OpenAI.",
            },
        }

    matches = [m for m in result_json.get("matches", []) if m.get("tin")]

    if not matches:
        return {
            "via": "openai",
            "results": {
                "matches": [],
                "needs_clarification": True,
                "explanation": result_json.get(
                    "explanation", "No verified US-based charities with a valid EIN were found."
                ),
            },
        }

    # Sort by location + confidence
    matches.sort(key=lambda m: (m.get("location", "").lower(), -m.get("confidence", 0)))

    return {
        "via": "openai",
        "results": {
            "matches": matches,
            "needs_clarification": result_json.get("needs_clarification", False),
            "explanation": result_json.get("explanation", ""),
        },
    }


# -----------------------------------------------------------------------------
# Core DB search logic (shared by /ai-search/ and /ai/)
# -----------------------------------------------------------------------------

def _perform_database_search(name: str, tin: str):
    """
    Search local Charity table by name and/or TIN.
    Returns (matches_serialized, any_enriched, needs_clarification).
    """
    filters = Q()
    if name:
        filters &= Q(name__icontains=name)
    if tin:
        filters &= Q(tin__iexact=tin)

    matches = Charity.objects.filter(filters).distinct()

    if not matches.exists():
        return [], False, False

    def name_similarity(a, b):
        try:
            return SequenceMatcher(None, a.lower(), b.lower()).ratio()
        except Exception:
            return 0.0

    if name:
        matches = sorted(matches, key=lambda c: name_similarity(name, c.name), reverse=True)

    MAX_ENRICH = 5
    enriched = []
    any_updated = False

    for idx, charity in enumerate(matches):
        contact_missing = not (
            charity.website or charity.contact_email or charity.contact_telephone
        )

        if contact_missing and idx < MAX_ENRICH:
            info = get_charity_contact_info(charity.name, charity.address or "")
            updated = False
            if info.get("website"):
                charity.website = info["website"]
                updated = True
            if info.get("emails"):
                charity.contact_email = info["emails"][0]
                updated = True
            if info.get("phones"):
                charity.contact_telephone = info["phones"][0]
                updated = True

            if updated:
                charity.save()
                any_updated = True
                print(f"[ENRICHED] {charity.name}")

        enriched.append(CharitySerializer(charity).data)

    needs_clarification = len(enriched) > 1
    return enriched, any_updated, needs_clarification


def _perform_search(name: str, tin: str, request):
    """
    High-level search:
    1) Fast EIN lookup
    2) Name/TIN DB search
    3) OpenAI fallback
    Returns a dict in the shapes your frontend expects.
    """
    previous_context = _get_context_from_session(request)
    user_input = name or tin

    # 1) Fast EIN lookup
    if tin:
        charity = Charity.objects.filter(tin__iexact=tin).first()
        if charity:
            serializer = CharitySerializer(charity)
            ai_output = f"Found {charity.name} by EIN."
            _update_context_session(request, user_input, ai_output)
            payload = {
                "source": "database",
                "via": "database",
                "message": "Found charity by EIN (no enrichment needed).",
                "matches": [serializer.data],
                "needs_clarification": False,
                "enrichment_done": False,
            }
            _store_last_matches(request, payload["matches"])
            return payload
        else:
            print(f"[FAST EIN LOOKUP] No match for EIN {tin}")
            openai_result = _search_with_openai(f'EIN (TIN) "{tin}"', previous_context)
            _update_context_session(request, user_input, openai_result.get("results", {}).get("explanation", ""))
            if openai_result.get("via") == "openai":
                _store_last_matches(request, openai_result["results"]["matches"])
            return openai_result

    # 2) DB search by name (and optional tin)
    matches, any_updated, needs_clarification = _perform_database_search(name, tin)
    if matches:
        msg = (
            "Single charity record found."
            if len(matches) == 1
            else f"Multiple charities found. Showing top {len(matches)}."
        )
        payload = {
            "source": "database",
            "via": "database",
            "message": msg,
            "matches": matches,
            "needs_clarification": needs_clarification,
            "enrichment_done": any_updated,
        }
        _store_last_matches(request, payload["matches"])
        _update_context_session(request, user_input, msg)
        return payload

    # 3) OpenAI fallback when DB has no match
    descriptor = f'name "{name}"' if name else f'EIN "{tin}"'
    openai_result = _search_with_openai(descriptor, previous_context)
    if openai_result.get("via") == "openai":
        _store_last_matches(request, openai_result["results"]["matches"])
    _update_context_session(request, user_input, openai_result.get("results", {}).get("explanation", ""))
    return openai_result


# -----------------------------------------------------------------------------
# Public endpoints
# -----------------------------------------------------------------------------

@csrf_exempt
@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def ai_search_charity(request):
    """
    Direct search endpoint (used if you ever want /ai-search/ on its own).
    Your React popup now mainly uses /ai/, but this stays for compatibility.
    """
    print("[AI SEARCH]", request.data)
    name = (request.data.get("charity_name") or request.data.get("name") or "").strip()
    tin = (request.data.get("tin") or "").strip()

    if not name and not tin:
        return Response({"error": "charity_name or EIN required"}, status=status.HTTP_400_BAD_REQUEST)

    result = _perform_search(name, tin, request)
    return Response(result, status=status.HTTP_200_OK)


# ---- Chat + search router used by your popup (/ai/) -------------------------

def _filter_results(matches, message: str):
    """Filter a list of match dicts based on address/location keywords."""
    filtered = []
    msg_lower = message.lower()
    tokens = [t for t in re.split(r"\s+", msg_lower) if t]

    for m in matches:
        combined = f"{m.get('address', '')} {m.get('location', '')}".lower()
        if all(tok in combined for tok in tokens):
            filtered.append(m)

    return filtered


def _clarify_with_openai(message: str, request, last_matches=None):
    """Ask GPT for a clarification reply."""
    previous_context = _get_context_from_session(request)
    context_text = f"\nPrevious context:\n{previous_context}\n" if previous_context else ""
    match_text = ""
    if last_matches:
        top = "\n".join([f"- {m.get('name')} ({m.get('location', '')})" for m in last_matches[:5]])
        match_text = f"\nRecent results:\n{top}\n"

    prompt = f"""
You are a helpful assistant for verified US charities.

User said: "{message}"
{context_text}
{match_text}

If this seems like a refinement (e.g., specifying city, state, or road),
respond with a brief clarification question.
Do NOT invent charities or EINs.
"""

    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.4,
            messages=[
                {"role": "system", "content": "You are a factual assistant for US charity data."},
                {"role": "user", "content": prompt},
            ],
            timeout=15,
        )
        reply = completion.choices[0].message.content
        _update_context_session(request, message, reply)
        return {
            "via": "openai-clarifier",
            "reply": reply,
        }
    except Exception as e:
        print(f"[OpenAI Clarifier Error] {e}")
        return {"via": "openai-clarifier", "reply": "I had trouble processing that. Could you rephrase it?"}


@csrf_exempt
@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def ai_router(request):
    """
    Unified endpoint used by the frontend:
    - Decides if the message is a NEW SEARCH or a FILTER/CHAT
    - Uses DB + OpenAI via _perform_search
    - Supports refinement via 'via: "filter"' and 'via: "openai-clarifier"'
    """
    message = (request.data.get("message") or "").strip()
    explicit_name = (request.data.get("charity_name") or "").strip()
    explicit_tin = (request.data.get("tin") or "").strip()

    if not message and not explicit_name and not explicit_tin:
        return Response({"error": "message is required"}, status=status.HTTP_400_BAD_REQUEST)

    # Small helper: detect if message looks like an EIN
    def looks_like_tin(text: str):
        digits = re.sub(r"\D", "", text)
        return digits.isdigit() and 7 <= len(digits) <= 9

    msg_lower = message.lower()
    search_keywords = ["find", "search", "lookup", "charity", "organization", "ein", "tin"]
    is_search_keyword = any(k in msg_lower for k in search_keywords)
    is_short_query = len(message.split()) <= 3
    is_tin_query = looks_like_tin(message)

    last_matches = _get_last_matches(request)

    # Decide if this is a new search
    is_new_search = (
        explicit_name
        or explicit_tin
        or is_search_keyword
        or is_tin_query
        or (not last_matches)  # no previous context = must be new search
    )

    if is_new_search:
        # Derive name/tin from explicit fields or message
        name = explicit_name
        tin = explicit_tin

        if not name and not tin:
            if is_tin_query:
                tin = re.sub(r"\D", "", message)
            else:
                name = message

        print(f"[ROUTER] NEW SEARCH → name='{name}', tin='{tin}'")
        result = _perform_search(name, tin, request)
        return Response(result, status=status.HTTP_200_OK)

    # Otherwise: refinement / filtering over last_matches
    print("[ROUTER] REFINEMENT / FILTER MODE")
    filtered = _filter_results(last_matches, message)
    if filtered:
        _store_last_matches(request, filtered)
        _update_context_session(request, message, f"Filtered to {len(filtered)} results.")
        return Response(
            {"via": "filter", "message": f"Filtered results based on '{message}'", "matches": filtered},
            status=status.HTTP_200_OK,
        )

    # If no local filter, ask GPT to clarify
    clarify_payload = _clarify_with_openai(message, request, last_matches)
    return Response(clarify_payload, status=status.HTTP_200_OK)

@csrf_exempt
@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def ai_filter_charities(request):
    """
    Takes a list of charity dicts (from previous search) + user filter text,
    and uses GPT to return a filtered subset with reasoning.
    """
    try:
        data = request.data
        filter_text = data.get("filter_text", "").strip()
        charities = data.get("charities", [])
        if not filter_text or not charities:
            return Response({"error": "filter_text and charities are required."},
                            status=status.HTTP_400_BAD_REQUEST)

        # Limit to 100 max to save tokens
        charities = charities[:100]

        # Build prompt
        prompt = f"""
You are an intelligent charity data filter.
The user wants to filter the charity list below based on this instruction:
"{filter_text}"

You will read the JSON list and return only those entries that match the intent.

RULES:
- Never invent new charities or change data.
- If uncertain, include slightly broader results.
- Return only JSON in the format:
{{"filtered": [ ...subset of original charities... ], "reason": "explain briefly"}}

Here is the data (JSON list):
{json.dumps(charities, indent=2)}
"""

        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.3,
            messages=[
                {"role": "system", "content": "You are a precise assistant that filters JSON lists."},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            timeout=25,
        )

        result = completion.choices[0].message.content
        parsed = json.loads(result)
        filtered = parsed.get("filtered", [])
        reason = parsed.get("reason", "Filtered based on given instruction.")

        print(f"[AI FILTER] '{filter_text}' → {len(filtered)} results")

        return Response({
            "via": "openai-filter",
            "message": reason,
            "matches": filtered,
            "filter_text": filter_text
        }, status=200)

    except Exception as e:
        print(f"[AI FILTER ERROR] {e}")
        return Response({
            "via": "openai-filter",
            "error": str(e),
            "matches": [],
            "message": "AI filter failed."
        }, status=500)
