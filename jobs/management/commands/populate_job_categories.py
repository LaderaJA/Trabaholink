"""
Management command to populate JobCategory table with common job categories.
Usage: python manage.py populate_job_categories
"""
from django.core.management.base import BaseCommand
from jobs.models import JobCategory


class Command(BaseCommand):
    help = 'Populate JobCategory table with common job categories'

    def handle(self, *args, **options):
        """Populate the JobCategory table"""
        
        # List of job categories
        categories = [
            # Construction & Trades
            "Carpentry",
            "Masonry",
            "Painting",
            "Welding",
            "Plumbing",
            "Electrical Work",
            "Roofing",
            "Tiling",
            "Concrete Work",
            "Construction Labor",
            
            # Home Services
            "House Cleaning",
            "Laundry Services",
            "Gardening",
            "Landscaping",
            "Pest Control",
            "Appliance Repair",
            "Furniture Assembly",
            "Moving & Hauling",
            "Junk Removal",
            
            # Technical Services
            "Computer Repair",
            "Phone Repair",
            "Network Installation",
            "CCTV Installation",
            "Aircon Cleaning & Repair",
            "Appliance Installation",
            
            # Automotive
            "Auto Repair",
            "Auto Detailing",
            "Tire Services",
            "Motorcycle Repair",
            
            # Personal Services
            "Hair Cutting",
            "Massage Therapy",
            "Beauty Services",
            "Tailoring & Sewing",
            "Catering",
            "Event Planning",
            "Photography",
            "Videography",
            
            # Tutoring & Education
            "Academic Tutoring",
            "Music Lessons",
            "Language Lessons",
            "Skills Training",
            
            # Delivery & Transportation
            "Delivery Services",
            "Courier Services",
            "Driver Services",
            "Trucking Services",
            
            # Professional Services
            "Accounting",
            "Legal Services",
            "Graphic Design",
            "Web Development",
            "Content Writing",
            "Translation Services",
            "Virtual Assistant",
            
            # Care Services
            "Childcare",
            "Elderly Care",
            "Pet Care",
            "Pet Grooming",
            
            # Maintenance & Repair
            "General Maintenance",
            "Door & Window Repair",
            "Furniture Repair",
            "Lock & Key Services",
            
            # Specialized Services
            "Security Services",
            "Janitorial Services",
            "Warehouse Work",
            "Factory Work",
            "Farm Labor",
            
            # Other
            "Others",
        ]
        
        created_count = 0
        existing_count = 0
        
        self.stdout.write(self.style.MIGRATE_HEADING('Populating Job Categories...'))
        
        for category_name in categories:
            category, created = JobCategory.objects.get_or_create(name=category_name)
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'  ✓ Created: {category_name}')
                )
            else:
                existing_count += 1
                self.stdout.write(
                    self.style.WARNING(f'  - Already exists: {category_name}')
                )
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'Summary:'))
        self.stdout.write(self.style.SUCCESS(f'  Created: {created_count} categories'))
        self.stdout.write(self.style.WARNING(f'  Existing: {existing_count} categories'))
        self.stdout.write(self.style.SUCCESS(f'  Total: {created_count + existing_count} categories'))
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Job categories populated successfully!'))
