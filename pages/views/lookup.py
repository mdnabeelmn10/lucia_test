import uuid
import requests, re
from bs4 import BeautifulSoup
import json
from urllib.parse import urljoin, urlparse
import os
from difflib import SequenceMatcher

from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status,permissions

from ..models import Charity
from ..serializers import CharitySerializer
from ..permissions import IsLuciaAdmin, IsLuciaDirector
from django.db.models import Q


from openai import OpenAI

client = OpenAI()

SERP_API_KEY = os.getenv("SERP_API_KEY")

def get_charity_contact_info(charity_name):
    serp_url = "https://serpapi.com/search.json"
    params = {
        "engine": "google",
        "q": f"{charity_name} official site",
        "api_key": SERP_API_KEY
    }

    try:
        res = requests.get(serp_url, params=params, timeout=10)
        data = res.json()
        website = None
        if "organic_results" in data and len(data["organic_results"]) > 0:
            website = data["organic_results"][0].get("link", None)
    except Exception as e:
        print(f"Google search failed for {charity_name}: {e}")
        return {"website": None, "emails": [], "phones": []}

    if not website:
        print(f"No website found for {charity_name}")
        return {"website": None, "emails": [], "phones": []}

    def scrape_page(url):
        try:
            html = requests.get(url, timeout=10).text
            # emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(?<!\.\d{1,3})',html)
            emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[A-Za-z]{2,}',html)
            phones = re.findall(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', html)
            emails = list(set([e for e in emails if not e.endswith((".png", ".jpg", ".jpeg","1","2","3","4","5","6","7","8","9","0"))]))
            phones = list(set(phones))
            return emails, phones, html
        except Exception as e:
            print(f"Error scraping {url}: {e}")
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

    final = {"website": website, "emails": all_emails, "phones": all_phones}
    # print(final)
    return final

@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def search_and_update_charity(request):
    charity_name = request.data.get("charity_name") or request.data.get("name")
    tin = request.data.get("tin")

    if not charity_name and not tin:
        return Response(
            {"error": "Either charity_name or tin is required."},
            status=status.HTTP_400_BAD_REQUEST
        )

    matches = Charity.objects.filter(
        Q(name__icontains=charity_name) | Q(tin__iexact=tin)
    ).distinct()

    if not matches.exists():
        return Response(
            {"error": "Charity not found in local database. Only enrichment allowed."},
            status=status.HTTP_404_NOT_FOUND
        )

    def name_similarity(a, b):
        try:
            return SequenceMatcher(None, a.lower(), b.lower()).ratio()
        except Exception:
            return 0.0

    sorted_matches = sorted(
        matches,
        key=lambda c: name_similarity(charity_name, c.name),
        reverse=True
    )

    matches = sorted_matches[:20]  # return only top 20 most similar

    MAX_ENRICH = 5
    enriched = []
    any_updated = False

    for idx, charity in enumerate(matches):
        contact_missing = (
            (not charity.website or charity.website.strip() == "") and
            (not charity.contact_email or charity.contact_email.strip() == "") and
            (not charity.contact_telephone or charity.contact_telephone.strip() == "")
        )

        if contact_missing and idx < MAX_ENRICH:
            info = get_charity_contact_info(charity.name)
            needs_update = False

            if info.get("website"):
                charity.website = info["website"]
                needs_update = True
            if info.get("emails"):
                charity.contact_email = info["emails"][0]
                needs_update = True
            if info.get("phones"):
                charity.contact_telephone = info["phones"][0]
                needs_update = True

            if needs_update:
                charity.save()
                any_updated = True
                print(f"[Enriched] {charity.name}")
            else:
                print(f"[No new info] {charity.name}")

        else:
            if contact_missing:
                print(f"[Skipped enrichment for {charity.name}] (beyond top {MAX_ENRICH})")
            else:
                print(f"[Already complete] {charity.name}")

        enriched.append(CharitySerializer(charity).data)


    if len(enriched) == 1:
        return Response({
            "source": "database",
            "message": "Charity record processed successfully.",
            "matches": enriched,
            "needs_clarification": False,
            "enrichment_done": any_updated
        }, status=status.HTTP_200_OK)

    return Response({
        "source": "database",
        "message": f"Multiple charities found. Showing top {len(enriched)} and enriched top {MAX_ENRICH}.",
        "matches": enriched,
        "needs_clarification": True,
        "enrichment_done": any_updated
    }, status=status.HTTP_200_OK)

# @api_view(["POST"])
# @permission_classes([permissions.AllowAny])
# def search_and_update_charity(request):

#     charity_name = request.data.get("charity_name") or request.data.get("name")
#     tin = request.data.get("tin")

#     if not charity_name and not tin:
#         return Response({"error": "Either charity_name or tin is required."},
#                         status=status.HTTP_400_BAD_REQUEST)

#     from django.db.models import Q
#     matches = Charity.objects.filter(
#         Q(name__icontains=charity_name) | Q(tin__iexact=tin)
#     ).distinct()

#     if not matches.exists():
#         return Response(
#             {"error": "Charity not found in local database. Only enrichment allowed."},
#             status=status.HTTP_404_NOT_FOUND
#         )

#     enriched = []
#     any_updated = False

#     # ✅ Iterate through all matches — enrich any missing info
#     for charity in matches:
#         contact_missing = (
#             (not charity.website or charity.website.strip() == "") and
#             (not charity.contact_email or charity.contact_email.strip() == "") and
#             (not charity.contact_telephone or charity.contact_telephone.strip() == "")
#         )

#         if contact_missing:
#             info = get_charity_contact_info(charity.name)
#             needs_update = False

#             if info.get("website"):
#                 charity.website = info["website"]
#                 needs_update = True
#             if info.get("emails"):
#                 charity.contact_email = info["emails"][0]
#                 needs_update = True
#             if info.get("phones"):
#                 charity.contact_telephone = info["phones"][0]
#                 needs_update = True

#             if needs_update:
#                 charity.save()
#                 any_updated = True
#                 print(f"[Enriched] {charity.name}")
#             else:
#                 print(f"[No new info] {charity.name}")

#         else:
#             print(f"[Already complete] {charity.name}")

#         enriched.append(CharitySerializer(charity).data)

#     # ✅ Build unified response
#     if len(enriched) == 1:
#         return Response({
#             "source": "database",
#             "message": "Charity record processed successfully.",
#             "matches": enriched,
#             "needs_clarification": False,
#             "enrichment_done": any_updated
#         }, status=status.HTTP_200_OK)

#     return Response({
#         "source": "database",
#         "message": "Multiple charities found and processed.",
#         "matches": enriched,
#         "needs_clarification": True,  # still multiple matches
#         "enrichment_done": any_updated
#     }, status=status.HTTP_200_OK)


# @api_view(["POST"])
# @permission_classes([])
# def search_and_update_charity(request):
#     # charity_name = request.data.get("charity_name")
#     charity_name = request.data.get("charity_name") or request.data.get("name")

#     tin = request.data.get("tin")

#     if not charity_name and not tin:
#         return Response({"error": "Either charity_name or tin is required."},
#                         status=status.HTTP_400_BAD_REQUEST)

#     matches = Charity.objects.filter(
#     Q(name__icontains=charity_name) | Q(tin__iexact=tin)).distinct()

#     if not matches.exists():
#         return Response({"error": "Charity not found"}, status=404)

#     # Single match
#     if matches.count() == 1:
#         serializer = CharitySerializer(matches.first())
#         return Response({
#             "source": "database",
#             "matches": [serializer.data],
#             "needs_clarification": False,
#             "message": "Single match found in database."
#         }, status=200)

#     # Multiple matches
#     serializer = CharitySerializer(matches, many=True)
#     return Response({
#         "source": "database",
#         "matches": serializer.data,
#         "needs_clarification": True,
#         "message": "Multiple similar charities found."
#     }, status=200)
    

#     if not charity:
#         return Response({"error": "Charity not found in local database. Only enrichment allowed."},
#                         status=status.HTTP_404_NOT_FOUND)

#     # ✅ Enrich ONLY if ALL 3 are empty/None
#     contact_missing = (
#         (charity.website is None or charity.website.strip() == "")
#         or (charity.contact_email is None or charity.contact_email.strip() == "")
#         and (charity.contact_telephone is None or charity.contact_telephone.strip() == "")
#     )

#     if not contact_missing:
#         serializer = CharitySerializer(charity)
#         print("Found")
#         return Response({
#             "message": "Charity already exists.",
#             "charity": serializer.data
#         }, status=status.HTTP_200_OK)


#     # ✅ Allowed to enrich
#     info = get_charity_contact_info(charity.name)

#     needs_update = False

#     if info.get("website"):
#         charity.website = info["website"]
#         needs_update = True

#     if info.get("emails"):
#         charity.contact_email = info["emails"][0]
#         needs_update = True

#     if info.get("phones"):
#         charity.contact_telephone = info["phones"][0]
#         needs_update = True

#     if needs_update:
#         charity.save()
#         serializer = CharitySerializer(charity)
#         print("message"+ "Enrichment successful!")
#         return Response(
#             {"message": "Enrichment successful!", "charity": serializer.data},
#             status=status.HTTP_200_OK
#         )
    
#     serializer = CharitySerializer(charity)
#     return Response(
#         {"message": "No contact info found online. Nothing updated.","charity": serializer.data},
#         status=status.HTTP_200_OK
#     )

# @api_view(["POST"])
# @permission_classes([permissions.AllowAny])
# def ai_search_charity(request):
#     """
#     - Accepts: { "charity_name": "..." } (or "name")
#     - Flow:
#       1. Try existing internal lookup (/search-and-update-charity). If found -> return via "database".
#       2. If not found -> call OpenAI to suggest candidates (US-only), return structured JSON:
#          {
#            "via": "openai",
#            "results": {
#              "matches": [...],
#              "needs_clarification": true|false,
#              "explanation": "short paragraph about the likely org"
#            }
#          }
#     - Matches include: name, location, type, website, address, contact_email, contact_phone, confidence (0-1), tin (EIN) if available
#     """
#     name = request.data.get("charity_name") or request.data.get("name")
#     if not name:
#         return Response({"error": "charity_name is required"}, status=status.HTTP_400_BAD_REQUEST)

#     # 1) Call existing internal lookup API
#     test_client = Client()
#     internal_res = test_client.post(
#         "/search-and-update-charity",
#         data=json.dumps({"charity_name": name}),
#         content_type="application/json"
#     )

#     # If internal service returns success (not 404) -> return DB result and stop (NO CHATBOT)
#     if internal_res.status_code != 404:
#         try:
#             payload = internal_res.json()
#         except Exception:
#             return Response({
#                 "via": "database",
#                 "data": None,
#                 "note": "internal lookup returned non-JSON payload"
#             }, status=200)
#         return Response({
#             "via": "database",
#             "data": payload
#         }, status=200)

#     # 2) Not found in local DB -> ask OpenAI to search
#     # We'll instruct the model to return JSON only and to restrict to US-based institutions.
#     prompt = f"""
# You are an assistant that helps identify institutions (charity, church, college, non-profit).
# The user searched for: "{name}"

# Rules:
# - Only return institutions located in the United States (US). If no clear US match exists, say "no_us_match".
# - Always produce a JSON object only (no extra text).
# - The JSON must be:
# {{
#   "matches": [
#     {{
#       "name": "",
#       "location": "",        // city, state (e.g. "Seattle, WA")
#       "type": "",            // charity/church/college/other
#       "website": "",
#       "address": "",
#       "contact_email": "",
#       "contact_phone": "",
#       "tin": "",             // EIN if known, otherwise empty string
#       "confidence": 0.0
#     }}
#   ],
#   "needs_clarification": true_or_false,
#   "explanation": "short paragraph (1-3 sentences) about why these matches were suggested"
# }}

# Instructions:
# - If the model finds multiple plausible US matches, include them in "matches" and set "needs_clarification" true.
# - If the model finds one clear US match, return only that in "matches" and set "needs_clarification" false.
# - If the model cannot find a US match, return "matches": [] and explanation "no_us_match".
# - Try to fill 'tin' (EIN) if known. If EIN is missing, leave blank and later the frontend should request EIN from the user.
# - Confidence should be between 0.0 and 1.0.
# - Keep all strings concise. Output must be strict JSON parsable.
# """

#     try:
#         completion = client.chat.completions.create(
#             model="gpt-4o-mini",
#             messages=[{"role": "user", "content": prompt}],
#             response_format={"type": "json_object"}
#         )
#         # Depending on SDK, the structured content can be inside:
#         raw = completion.choices[0].message.content
#         # raw should be a JSON string or dict-like depending on the SDK's response_format handling.
#         # We'll try to coerce it into a dict.
#         if isinstance(raw, (dict, list)):
#             result_json = raw
#         else:
#             result_json = json.loads(raw)
#     except Exception as e:
#         # Fallback: if OpenAI fails, return helpful error for frontend
#         return Response({
#             "via": "openai",
#             "error": "OpenAI call failed",
#             "detail": str(e)
#         }, status=500)

#     # Validate structure and enforce US-only rule at backend level:
#     matches = result_json.get("matches", [])
#     filtered_matches = []
#     for m in matches:
#         # basic safety: lower-case location and check for 'us' or 'united states' or state abbreviations
#         loc = (m.get("location") or "").lower()
#         is_us = False
#         if not loc:
#             # if location empty, we can't assume US - mark not included
#             is_us = False
#         else:
#             # crude but practical checks
#             if "united states" in loc or "usa" in loc or "us" in loc:
#                 is_us = True
#             # check for "City, ST" pattern with a two-letter state code (ex: "Seattle, WA")
#             if len(loc.split(",")) == 2:
#                 part2 = loc.split(",")[1].strip()
#                 if len(part2) == 2 and part2.isalpha():
#                     is_us = True
#         if is_us:
#             filtered_matches.append(m)

#     # If OpenAI predicted non-US or nothing US, return "no_us_match" message
#     if not filtered_matches:
#         return Response({
#             "via": "openai",
#             "results": {
#                 "matches": [],
#                 "needs_clarification": False,
#                 "explanation": "no_us_match"
#             }
#         }, status=200)

#     # Post-process: flag matches that require EIN (tin) and sanitize
#     processed = []
#     for m in filtered_matches:
#         proc = {
#             "name": m.get("name", "").strip(),
#             "location": m.get("location", "").strip(),
#             "type": m.get("type", "").strip(),
#             "website": m.get("website", "").strip(),
#             "address": m.get("address", "").strip(),
#             "contact_email": m.get("contact_email", "").strip(),
#             "contact_phone": m.get("contact_phone", "").strip(),
#             "tin": m.get("tin", "").strip(),
#             "confidence": float(m.get("confidence", 0.0))
#         }
#         proc["requires_ein"] = (proc["tin"] == "")

#         processed.append(proc)

#     needs_clarification = result_json.get("needs_clarification", False)
#     explanation = result_json.get("explanation", "")

#     return Response({
#         "via": "openai",
#         "results": {
#             "matches": processed,
#             "needs_clarification": needs_clarification,
#             "explanation": explanation
#         }
#     }, status=200)


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def ai_search_charity(request):
    name = request.data.get("charity_name") or request.data.get("name")
    tin = request.data.get("tin")

    if not name and not tin:
        return Response({"error": "charity_name or EIN required"}, status=400)

    # Call lookup first
    from django.test import Client
    test_client = Client()
    internal_res = test_client.post(
        "/lookup/",
        data=json.dumps({"charity_name": name, "tin": tin}),
        content_type="application/json"
    )

    if internal_res.status_code == 200:
        payload = internal_res.json()
        payload["via"] = "database"
        return Response(payload, status=200)

    # Not found locally → AI Search
    prompt = f"""
You are an assistant that helps identify verified US-based organizations (charities, colleges, churches).
The user searched for: "{name}".
You must only return organizations based in the United States.

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
      "tin": "",  // EIN - must be present, mandatory
      "confidence": 0.0
    }}
  ],
  "needs_clarification": true|false,
  "explanation": "brief explanation"
}}

Rules:
- Only return US-based entities.
- Do not include non-US organizations.
- EIN (tin) is mandatory for every match. If EIN is not found, omit that match entirely.
"""

    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        raw = completion.choices[0].message.content
        result_json = json.loads(raw) if isinstance(raw, str) else raw
    except Exception as e:
        return Response({"via": "openai", "error": str(e)}, status=500)

    # Validate EIN presence
    matches = [m for m in result_json.get("matches", []) if m.get("tin")]

    if not matches:
        return Response({
            "via": "openai",
            "results": {
                "matches": [],
                "needs_clarification": False,
                "explanation": "No valid US-based matches with EIN found."
            }
        }, status=200)

    return Response({
        "via": "openai",
        "results": {
            "matches": matches,
            "needs_clarification": result_json.get("needs_clarification", False),
            "explanation": result_json.get("explanation", "")
        }
    }, status=200)
