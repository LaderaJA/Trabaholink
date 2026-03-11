"""
Django management command to add blue collar job service categories
Usage: python manage.py add_service_categories
"""
from django.core.management.base import BaseCommand
from services.models import ServiceCategory


class Command(BaseCommand):
    help = 'Add blue collar job service categories to the database'

    def handle(self, *args, **options):
        # Blue collar job categories
        categories = [
            # Construction & Building
            "Carpentry",
            "Masonry",
            "Plumbing",
            "Electrical Work",
            "Welding",
            "Painting",
            "Tiling",
            "Roofing",
            "Concrete Work",
            
            # Home Services
            "House Cleaning",
            "Laundry Services",
            "Gardening",
            "Landscaping",
            "Pest Control",
            "Appliance Repair",
            "Furniture Assembly",
            
            # Vehicle & Transportation
            "Auto Repair",
            "Motorcycle Repair",
            "Driver Services",
            "Delivery Services",
            
            # Technical Services
            "Air Conditioning Repair",
            "CCTV Installation",
            "Computer Repair",
            "Phone Repair",
            
            # Personal Services
            "Hair Styling",
            "Massage Therapy",
            "Tailoring & Sewing",
            "Catering Services",
            "Event Services",
            
            # Other Manual Labor
            "Moving Services",
            "Loading & Unloading",
            "General Labor",
            "Janitorial Services",
            "Security Services",
        ]

        self.stdout.write("=" * 60)
        self.stdout.write(self.style.SUCCESS("🔧 ADDING BLUE COLLAR JOB SERVICE CATEGORIES"))
        self.stdout.write("=" * 60)
        
        created_count = 0
        existing_count = 0
        
        for category_name in categories:
            category, created = ServiceCategory.objects.get_or_create(
                name=category_name
            )
            
            if created:
                self.stdout.write(self.style.SUCCESS(f"✅ Created: {category_name}"))
                created_count += 1
            else:
                self.stdout.write(self.style.WARNING(f"ℹ️  Already exists: {category_name}"))
                existing_count += 1
        
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS(f"📊 SUMMARY:"))
        self.stdout.write(f"   ✅ New categories added: {created_count}")
        self.stdout.write(f"   ℹ️  Already existed: {existing_count}")
        self.stdout.write(f"   📋 Total categories: {ServiceCategory.objects.count()}")
        self.stdout.write("=" * 60)
        
        # Show all categories
        self.stdout.write("\n📋 ALL SERVICE CATEGORIES:")
        self.stdout.write("-" * 60)
        all_categories = ServiceCategory.objects.all().order_by('name')
        for i, cat in enumerate(all_categories, 1):
            post_count = cat.service_posts.count()
            self.stdout.write(f"{i:2d}. {cat.name:<30} ({post_count} posts)")
        self.stdout.write("-" * 60)
        
        self.stdout.write(self.style.SUCCESS("\n✅ Command completed successfully!"))
