import uuid
import requests, re
from bs4 import BeautifulSoup
import json
from urllib.parse import urljoin, urlparse
import os

from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status,permissions

from ..models import Charity
from ..serializers import CharitySerializer
from ..permissions import IsLuciaAdmin, IsLuciaDirector

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
            emails = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', html)
            phones = re.findall(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', html)
            emails = list(set([e for e in emails if not e.endswith((".png", ".jpg", ".jpeg"))]))
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
@permission_classes([permissions.IsAuthenticated])
def search_and_add_charity(request):
    charity_name = request.data.get("charity_name")
    if not charity_name:
        return Response({"error": "Charity name is required."}, status=status.HTTP_400_BAD_REQUEST)
    c = charity_name.capitalize()
    existing = Charity.objects.filter(name__iexact=c).first()
    if existing:
        serializer = CharitySerializer(existing)
        return Response({
            "message": "Charity already exists.",
            "charity": serializer.data
        }, status=status.HTTP_200_OK)

    try:
        search_url = f"https://projects.propublica.org/nonprofits/api/v2/search.json?q={charity_name}"
        res = requests.get(search_url, timeout=10)
        data = res.json()
        if not data.get("organizations"):
            return Response({"error": "No results found on ProPublica."}, status=status.HTTP_404_NOT_FOUND)

        top = data["organizations"][0]
        tin = str(top.get("ein", ""))
        API_URL = f"https://projects.propublica.org/nonprofits/api/v2/organizations/{tin}.json"

        res = requests.get(API_URL, timeout=10) 
        data = res.json().get("organization", {})

        if res.status_code == 200:
            address = f"{data.get('address', '')}, {data.get('city', '')}, {data.get('state', '')}, {data.get('zipcode', '')}"
            tax_exempt = data.get("exempt_organization_status_code") == 1
            contact_name = (data.get("careofname") or "").replace('%','').strip().capitalize()
    except Exception as e:
        return Response({"error": f"Failed to fetch from ProPublica: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # 3️⃣ Get contact info using SerpAPI
    info = get_charity_contact_info(charity_name)

    # 4️⃣ Create new Charity record
    charity = Charity.objects.create(
        id=uuid.uuid4(),
        name=charity_name,
        tin=tin,
        address=address,
        website=info.get("website"),
        contact_name=contact_name,
        contact_email=info["emails"][0] if info["emails"] else None,
        contact_telephone=info["phones"][0] if info["phones"] else None,
        tax_exempt=tax_exempt,
    )

    charity.save()

    serializer = CharitySerializer(charity)
    return Response({
        "message": "Charity successfully added.",
        "charity": serializer.data
    }, status=status.HTTP_201_CREATED)
