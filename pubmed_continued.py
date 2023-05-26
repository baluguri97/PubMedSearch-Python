from bs4 import BeautifulSoup
import json
import ssl
from urllib.request import urlopen

try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    # Legacy Python that doesn't verify HTTPS certificates by default
    pass
else:
    # Handle target environment that doesn't support HTTPS verification
    ssl._create_default_https_context = _create_unverified_https_context

keyword = None
while not keyword:
    keyword_candidate = input("Enter the keyword to search publications with: ").strip()
    if len(keyword_candidate) > 0:
        keyword = keyword_candidate

num_references = None
while not num_references:
    try:
        num_references_candidate = int(
            input("Enter the number of references you would like to return at most: ").strip()
        )
        if num_references_candidate < 1:
            raise ValueError
        num_references = num_references_candidate
    except ValueError:
        print(f'ERROR: The provided number (i.e. "{num_references_candidate}") of references to return at most is not a positive integer!')

with urlopen(
    f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&retmode=json&retmax=20&sort=relevance&term={keyword}"
) as f:
    pubmed_json_data = json.loads(f.read())

pubmed_ids = ",".join(pubmed_json_data["esearchresult"]["idlist"])
with urlopen(f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id={pubmed_ids}") as f:
    pubmed_xml_data = BeautifulSoup(f.read(), "xml")

for article in pubmed_xml_data.find_all("PubmedArticle")[:num_references]:
    # Get all authors and format them as nicely as possible
    authors = [
        (
            ".".join(list(author.find("Initials").string)) +
            ". " +
            author.find("LastName").string
        ) if author.find("Initials") and author.find("LastName") else author.find("CollectiveName").string
        for author in article.find_all("Author")
        if (author.find("Initials") and author.find("LastName")) or author.find("CollectiveName")
    ]
    if len(authors) == 2:
        authors = authors[0] + " and " + authors[1]
    elif len(authors) > 2:
        authors = ", ".join(authors[:-1]) + ", and " + authors[-1]
    else:
        authors = authors[0] if len(authors) > 0 else ""

    # Get name of the article    
    article_title = article.find("ArticleTitle").string

    # Get the journal details
    journal = article.find("Journal")
    journal_title = journal.find("Title").string
    volume = journal.find("Volume").string
    issue = journal.find("Issue")
    volume_issue = volume
    if issue:
        volume_issue += f'({issue.string})'
    page_numbers = article.find("MedlinePgn")

    # Get and format the pulication date as nicely as possible
    pubdate = article.find("PubDate")
    month = pubdate.find("Month")
    year = pubdate.find("Year")
    if month:
        publication_date = f'({month.string}. {year.string})'
    elif year:
        publication_date = f'({year.string})'
    else:
        publication_date = f'({pubdate.find("MedlineDate").string})'
    
    # Get the article's Pubmed ID
    article_id = article.find("ArticleId", {"IdType": "pubmed"})

    # Get DOI/PII from the XML tree
    doi_pii_prefix, doi_pii = "DOI", article.find("ELocationID", {"EIdType": "doi"})
    if not doi_pii:
        doi_pii_prefix, doi_pii = "PII", article.find("ELocationID", {"EIdType": "pii"})
    
    # Get the abstract text
    abstract = article.find("AbstractText")

    # Format and print the authors, article title, volume/issue, page numbers and publication date on an own row.
    print(
        (f'{authors}, ' if len(authors) > 0 else "") + f'"{article_title}"',
        journal_title,
        volume_issue + f' pp. {page_numbers.string}' if page_numbers else "",
        f'{publication_date}.',
    )

    # Format and print the Pubmed ID and DOI/PII details in a separate row
    print(f'PUBMED: {article_id.string}' + (f'; {doi_pii_prefix} {doi_pii.string}' if doi_pii else "") + ".")

    # Print the abstract text if it exists
    if abstract and abstract.string:
        print(abstract.string)
    
    # Create a new line between the different publication citations
    print()
