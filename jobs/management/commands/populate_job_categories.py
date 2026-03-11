"""
Management command to populate JobCategory table with common job categories.
Usage: python manage.py populate_job_categories
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from jobs.models import JobCategory


class Command(BaseCommand):
    help = 'Populate JobCategory table with common job categories'

    def handle(self, *args, **options):
        """Populate the JobCategory table"""
        
        # List of job categories - Focused on skilled blue-collar and service jobs
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
            "Steel Fabrication",
            "Scaffolding",
            "Finishing Work",
            
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
            "Window Cleaning",
            
            # Technical Services
            "Computer Repair",
            "Phone Repair",
            "Network Installation",
            "CCTV Installation",
            "Aircon Cleaning & Repair",
            "Appliance Installation",
            "Solar Panel Installation",
            "Generator Repair",
            
            # Automotive & Motorcycles
            "Auto Repair",
            "Auto Detailing",
            "Tire Services",
            "Motorcycle Repair",
            "Auto Body Work",
            "Auto Painting",
            "Auto Electrical",
            
            # Personal Services
            "Hair Cutting",
            "Barbering",
            "Massage Therapy",
            "Beauty Services",
            "Nail Services",
            "Makeup Artist",
            "Tailoring & Sewing",
            "Shoe Repair",
            "Laundry & Ironing",
            "Catering",
            "Event Planning",
            "Photography",
            "Videography",
            
            # Food Services
            "Cook",
            "Baker",
            "Food Vendor",
            "Bartender",
            "Waiter/Waitress",
            
            # Tutoring & Education
            "Academic Tutoring",
            "Music Lessons",
            "Language Lessons",
            "Skills Training",
            "Driving Instructor",
            
            # Delivery & Transportation
            "Delivery Services",
            "Courier Services",
            "Food Delivery",
            "Grocery Delivery",
            "Errand Services",
            "Driver Services",
            "Tricycle Driver",
            "Pedicab Driver",
            "Trucking Services",
            "Pabili Services",
            
            # Professional Services
            "Accounting",
            "Legal Services",
            "Graphic Design",
            "Web Development",
            "Social Media Management",
            "Content Writing",
            "Translation Services",
            "Virtual Assistant",
            "Data Entry",
            "Transcription Services",
            "Online Selling Assistant",
            
            # Care Services
            "Childcare",
            "Babysitting",
            "Elderly Care",
            "Pet Care",
            "Pet Grooming",
            "Pet Walking",
            "Pet Sitting",
            "Housekeeping",
            "Nanny Services",
            "Companion Care",
            
            # Maintenance & Repair
            "General Maintenance",
            "Door & Window Repair",
            "Furniture Repair",
            "Lock & Key Services",
            "Refrigeration Repair",
            "Pump Repair",
            
            # Manufacturing & Industrial
            "Factory Work",
            "Warehouse Work",
            "Packaging Services",
            "Quality Control",
            "Machine Operation",
            "Assembly Line Work",
            
            # Agriculture & Farming
            "Farm Labor",
            "Crop Harvesting",
            "Livestock Care",
            "Fishing Services",
            "Agricultural Equipment Operation",
            
            # Specialized Services
            "Security Services",
            "Janitorial Services",
            "Septic Tank Cleaning",
            "Waterproofing",
            "Pool Maintenance",
            "Elevator Maintenance",
            
            # Side Hustles & Gig Economy
            "Party Host/Entertainer",
            "Event Staff",
            "Promotional Model",
            "Product Assembly",
            "Gift Wrapping",
            "Reselling/Buy & Sell",
            "Online Shop Assistant",
            "Car Washing",
            "Bike Repair",
            "Queue Services (Pila)",
            "Bill Payment Services",
            "Document Processing",
            "Printing Services",
            
            # Other
            "Other",
        ]
        
        created_count = 0
        existing_count = 0
        error_count = 0
        
        self.stdout.write(self.style.MIGRATE_HEADING('Populating Job Categories...'))
        
        # Process each category individually with its own transaction
        for category_name in categories:
            try:
                # Use individual atomic blocks for each category
                with transaction.atomic():
                    # Check if exists first (works better with modeltranslation)
                    exists = JobCategory.objects.filter(name=category_name).exists()
                    
                    if not exists:
                        # Create new category
                        category = JobCategory.objects.create(name=category_name)
                        created_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(f'  ✓ Created: {category_name}')
                        )
                    else:
                        existing_count += 1
                        self.stdout.write(
                            self.style.WARNING(f'  - Already exists: {category_name}')
                        )
            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(f'  ✗ Error with {category_name}: {str(e)}')
                )
                # Continue with other categories
                continue
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'Summary:'))
        self.stdout.write(self.style.SUCCESS(f'  Created: {created_count} categories'))
        self.stdout.write(self.style.WARNING(f'  Existing: {existing_count} categories'))
        if error_count > 0:
            self.stdout.write(self.style.ERROR(f'  Errors: {error_count} categories'))
        self.stdout.write(self.style.SUCCESS(f'  Total: {created_count + existing_count} categories'))
        self.stdout.write('')
        
        if error_count > 0:
            self.stdout.write(self.style.WARNING('Job categories populated with some errors.'))
        else:
            self.stdout.write(self.style.SUCCESS('Job categories populated successfully!'))
