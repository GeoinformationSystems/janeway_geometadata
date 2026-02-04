"""
Management command to load demo data for the geometadata plugin.

Creates demo articles with geographic and temporal metadata based on
data from the OJS geoMetadata Demo Journal.

Usage:
    python manage.py load_geometadata_demo --journal-code dqj
    python manage.py load_geometadata_demo --create-journal
    python manage.py load_geometadata_demo --create-journal --with-galleys
"""

__copyright__ = "Copyright 2025 TU Dresden / KOMET Project"
__author__ = "Daniel Nuest & KOMET Team"
__license__ = "AGPL v3"

import json
import os
from datetime import datetime

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from core.models import Account, File
from journal.models import Issue, Journal
from submission.models import Article, Keyword, Section


class Command(BaseCommand):
    help = "Load demo articles with geometadata from the geoMetadata Demo Journal"

    def add_arguments(self, parser):
        parser.add_argument(
            "--journal-code",
            type=str,
            default="dqj",
            help="Journal code to load demo data into (default: dqj)",
        )
        parser.add_argument(
            "--create-journal",
            action="store_true",
            help="Create the demo journal from demo_journal.json if it doesn't exist",
        )
        parser.add_argument(
            "--owner-email",
            type=str,
            default="admin@example.com",
            help="Email of the user to assign as article owner (default: admin@example.com)",
        )
        parser.add_argument(
            "--with-galleys",
            action="store_true",
            help="Also create PDF galleys using the placeholder file",
        )
        parser.add_argument(
            "--clear-existing",
            action="store_true",
            help="Clear existing demo articles before loading (matches by title prefix)",
        )

    def handle(self, *args, **options):
        journal_code = options["journal_code"]
        create_journal = options["create_journal"]
        owner_email = options["owner_email"]
        with_galleys = options["with_galleys"]
        clear_existing = options["clear_existing"]

        # Get or create journal
        if create_journal:
            journal = self._get_or_create_journal(journal_code)
        else:
            try:
                journal = Journal.objects.get(code=journal_code)
            except Journal.DoesNotExist:
                raise CommandError(
                    f"Journal with code '{journal_code}' not found. "
                    f"Use --create-journal to create it automatically."
                )

        self.stdout.write(f"Loading demo data into journal: {journal.name}")

        # Get or create owner account
        owner = self._get_or_create_owner(owner_email)
        self.stdout.write(f"Using owner account: {owner.email}")

        # Load demo data
        articles_data = self._load_json_file("demo_articles.json")
        issues_data = self._load_json_file("demo_issues.json")

        # Get or create section
        section = self._get_or_create_section(journal)

        if clear_existing:
            self._clear_existing_demo_articles(journal)

        # Create issues from separate file
        issues_by_key = {}
        for issue_data in issues_data["issues"]:
            issue = self._get_or_create_issue(journal, issue_data)
            key = (issue_data["volume"], str(issue_data["number"]))
            issues_by_key[key] = issue
            self.stdout.write(f"Created/found issue: {issue}")

        # Process articles and assign to issues
        total_articles = 0
        for issue_data in articles_data["issues"]:
            key = (issue_data["volume"], str(issue_data["number"]))
            issue = issues_by_key.get(key)
            if not issue:
                # Fallback: create issue from articles data
                issue = self._get_or_create_issue(journal, issue_data)
                issues_by_key[key] = issue

            self.stdout.write(f"Processing issue: {issue}")

            for article_data in issue_data["articles"]:
                article = self._create_article(
                    journal, issue, section, owner, article_data
                )
                self._create_geometadata(article, article_data.get("geometadata", {}))

                if with_galleys:
                    self._create_galley(article, owner)

                total_articles += 1
                self.stdout.write(f"  Created: {article.title[:60]}...")

        self.stdout.write(
            self.style.SUCCESS(f"Successfully created {total_articles} demo articles")
        )

    def _get_data_dir(self):
        """Get the path to the test/data directory."""
        return os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "test",
            "data",
        )

    def _load_json_file(self, filename):
        """Load a JSON file from the test/data directory."""
        data_file = os.path.join(self._get_data_dir(), filename)
        if not os.path.exists(data_file):
            raise CommandError(f"Data file not found: {data_file}")

        with open(data_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def _get_or_create_journal(self, journal_code):
        """Get or create the demo journal from demo_journal.json."""
        try:
            journal = Journal.objects.get(code=journal_code)
            self.stdout.write(f"Using existing journal: {journal.name}")
            return journal
        except Journal.DoesNotExist:
            pass

        # Load journal data
        journal_data = self._load_json_file("demo_journal.json")

        # Use code from argument if different from JSON
        if journal_code and journal_code != journal_data.get("code"):
            journal_data["code"] = journal_code

        # Get or create press (use first press available)
        from press.models import Press

        press = Press.objects.first()
        if not press:
            raise CommandError(
                "No press found. Please create a press before loading demo data."
            )

        # Create journal (automatically associated with press via press property)
        journal = Journal.objects.create(
            code=journal_data["code"],
            domain=f"{journal_data['code']}.localhost",
            is_remote=journal_data.get("is_remote", False),
            is_conference=journal_data.get("is_conference", False),
        )

        # Initialize all default settings for the journal (creates SettingValue records)
        from utils import install, setting_handler

        install.update_settings(journal, management_command=False)

        # Set journal name using the property setter (handles caching properly)
        journal.name = journal_data.get("name", journal_data["code"])

        # Set other journal settings
        settings_data = journal_data.get("settings", {})
        for setting_name, value in settings_data.items():
            # Skip journal_name since we set it above via the property
            if setting_name == "journal_name":
                continue
            try:
                setting_handler.save_setting("general", setting_name, journal, value)
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f"Could not save setting '{setting_name}': {e}")
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Created journal: {journal.name} ({journal_data['code']})"
            )
        )
        return journal

    def _get_or_create_owner(self, email):
        """Get or create the owner account for demo articles."""
        try:
            return Account.objects.get(email=email)
        except Account.DoesNotExist:
            # Create a demo user
            owner = Account.objects.create(
                email=email,
                username=email.split("@")[0],
                first_name="Demo",
                last_name="User",
                is_active=True,
            )
            owner.set_password("demo123")
            owner.save()
            self.stdout.write(
                self.style.WARNING(f"Created new user: {email} (password: demo123)")
            )
            return owner

    def _get_or_create_section(self, journal):
        """Get or create an 'Articles' section."""
        section, created = Section.objects.get_or_create(
            journal=journal,
            name="Articles",
            defaults={
                "plural": "Articles",
                "sequence": 0,
                "is_filterable": True,
                "public_submissions": True,
            },
        )
        if created:
            self.stdout.write(f"Created section: {section.name}")
        return section

    def _get_or_create_issue(self, journal, issue_data):
        """Get or create an issue."""
        issue, created = Issue.objects.get_or_create(
            journal=journal,
            volume=issue_data["volume"],
            issue=str(issue_data["number"]),
            defaults={
                "issue_title": issue_data.get("title", ""),
                "issue_description": issue_data.get("description", ""),
                "date": self._parse_datetime(issue_data.get("date_published")),
            },
        )

        if created:
            # Set issue type
            from journal.models import IssueType

            issue_type, _ = IssueType.objects.get_or_create(
                journal=journal,
                code="issue",
                defaults={"pretty_name": "Issue"},
            )
            issue.issue_type = issue_type
            issue.save()
            self.stdout.write(f"Created issue: Vol. {issue.volume} No. {issue.issue}")

        return issue

    def _create_article(self, journal, issue, section, owner, article_data):
        """Create an article from demo data."""
        # Parse publication date (use timezone-aware datetime)
        pub_datetime = self._parse_datetime(
            article_data.get(
                "date_published", issue.date.isoformat() if issue.date else None
            )
        )
        if not pub_datetime:
            pub_datetime = timezone.now()

        # Create article
        article = Article.objects.create(
            journal=journal,
            title=article_data["title"],
            abstract=article_data.get("abstract", ""),
            section=section,
            date_submitted=pub_datetime,
            date_accepted=pub_datetime,
            date_published=pub_datetime,
            stage="Published",
            owner=owner,
            correspondence_author=owner,
        )

        # Add to issue
        issue.articles.add(article)

        # Add authors
        for i, author_data in enumerate(article_data.get("authors", [])):
            self._add_author(article, author_data, i)

        # Add keywords
        for kw in article_data.get("keywords", []):
            keyword, _ = Keyword.objects.get_or_create(word=kw)
            article.keywords.add(keyword)

        article.save()
        return article

    def _add_author(self, article, author_data, order):
        """Add an author to the article."""
        from submission.models import FrozenAuthor

        # Check if account exists
        email = author_data.get(
            "email",
            f"{author_data['first_name'].lower()}.{author_data['last_name'].lower()}@example.com",
        )

        account = None
        try:
            account = Account.objects.get(email=email)
        except Account.DoesNotExist:
            pass

        FrozenAuthor.objects.create(
            article=article,
            first_name=author_data.get("first_name", ""),
            last_name=author_data.get("last_name", ""),
            institution=author_data.get("affiliation", ""),
            order=order,
            author=account,
        )

    def _create_geometadata(self, article, geo_data):
        """Create geometadata record for the article."""
        if not geo_data:
            return

        from plugins.geometadata.models import ArticleGeometadata

        # Parse temporal dates
        temporal_start = self._parse_date(geo_data.get("temporal_start"))
        temporal_end = self._parse_date(geo_data.get("temporal_end"))

        # Handle temporal periods as JSON array
        temporal_periods = []
        if temporal_start or temporal_end:
            temporal_periods = [
                [
                    temporal_start.isoformat() if temporal_start else "",
                    temporal_end.isoformat() if temporal_end else "",
                ]
            ]

        geometadata, _ = ArticleGeometadata.objects.update_or_create(
            article=article,
            defaults={
                "place_name": geo_data.get("place_name", ""),
                "admin_units": geo_data.get("admin_units", ""),
                "geometry_wkt": geo_data.get("geometry_wkt", ""),
                "temporal_periods": temporal_periods,
            },
        )
        return geometadata

    def _create_galley(self, article, owner):
        """Create a PDF galley from the placeholder file."""
        placeholder_path = os.path.join(self._get_data_dir(), "placeholder.pdf")

        if not os.path.exists(placeholder_path):
            self.stdout.write(
                self.style.WARNING(f"Placeholder PDF not found: {placeholder_path}")
            )
            return

        from core.models import Galley

        # Read the placeholder file
        with open(placeholder_path, "rb") as f:
            content = f.read()

        # Create a File object
        file_obj = File(
            article_id=article.pk,
            mime_type="application/pdf",
            original_filename="article.pdf",
            uuid_filename=f"article_{article.pk}.pdf",
            label="PDF",
            owner=owner,
        )
        file_obj.save()

        # Save the file content
        file_path = os.path.join(
            settings.BASE_DIR,
            "files",
            "articles",
            str(article.pk),
        )
        os.makedirs(file_path, exist_ok=True)
        full_path = os.path.join(file_path, file_obj.uuid_filename)
        with open(full_path, "wb") as f:
            f.write(content)

        # Create the galley
        galley = Galley.objects.create(
            article=article,
            file=file_obj,
            label="PDF",
            type="pdf",
            sequence=0,
        )

        return galley

    def _clear_existing_demo_articles(self, journal):
        """Clear existing demo articles (articles from demo issues)."""
        demo_titles = [
            "A quantitative spatial methodology",
            "An Etrusco-Italic Antefix",
            "Beach-ridge formation",
            "First report of the parasitoid wasp",
            "Analysis of the Housing Market",
            "Revisiting Conditional Typology",
            "Crowdsourcing air temperature",
            "Post-Brexit Power",
            "Islam and the Perception",
            "A record of magmatic differentiation",
            "The Coins from the 2023 Excavation",
            "Cooler and drier conditions",
            "Goods and Ethnicity",
            "Survival of the brightest",
            "The Digitalization of Local",
            "A shape-based heuristic",
            "Herrschaft vom Pferderuecken",
            "German Renewable Energy Policies",
        ]

        from django.db.models import Q

        query = Q()
        for title_prefix in demo_titles:
            query |= Q(title__startswith=title_prefix)

        articles = Article.objects.filter(journal=journal).filter(query)
        count = articles.count()
        if count > 0:
            # Delete associated geometadata first
            from plugins.geometadata.models import ArticleGeometadata

            ArticleGeometadata.objects.filter(article__in=articles).delete()
            articles.delete()
            self.stdout.write(
                self.style.WARNING(f"Deleted {count} existing demo articles")
            )

    def _parse_date(self, date_str):
        """Parse a date string, handling various formats including ancient dates."""
        if not date_str:
            return None

        # Handle ancient dates (negative years) - just return None for now
        if date_str.startswith("-"):
            return None

        try:
            # Try ISO format first
            return datetime.strptime(date_str[:10], "%Y-%m-%d").date()
        except (ValueError, TypeError):
            pass

        try:
            # Try just year
            year = int(date_str[:4])
            return datetime(year, 1, 1).date()
        except (ValueError, TypeError):
            pass

        return None

    def _parse_datetime(self, date_str):
        """Parse a date string and return a timezone-aware datetime."""
        date = self._parse_date(date_str)
        if date:
            return timezone.make_aware(datetime.combine(date, datetime.min.time()))
        return None
