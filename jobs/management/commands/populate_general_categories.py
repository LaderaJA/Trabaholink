from django.core.management.base import BaseCommand
from jobs.models import GeneralCategory, JobCategory


class Command(BaseCommand):
    help = 'Populate general categories and link job categories to them'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.MIGRATE_HEADING('Populating General Categories...'))
        
        # Define general categories with their job category mappings
        categories_mapping = {
            'construction': {
                'name': 'Construction & Trades',
                'icon': 'fas fa-hard-hat',
                'description': 'Construction, carpentry, masonry, electrical work, plumbing, and related trades',
                'job_categories': [
                    'Carpentry', 'Masonry', 'Painting', 'Welding', 'Plumbing', 
                    'Electrical Work', 'Roofing', 'Tiling', 'Concrete Work', 
                    'Construction Labor', 'Steel Fabrication', 'Scaffolding', 'Finishing Work'
                ]
            },
            'home_services': {
                'name': 'Home Services',
                'icon': 'fas fa-home',
                'description': 'House cleaning, laundry, gardening, and general home maintenance',
                'job_categories': [
                    'House Cleaning', 'Laundry Services', 'Laundry & Ironing', 'Gardening', 
                    'Landscaping', 'Pest Control', 'Furniture Assembly', 'Moving & Hauling', 
                    'Junk Removal', 'Window Cleaning'
                ]
            },
            'technical': {
                'name': 'Technical Services',
                'icon': 'fas fa-tools',
                'description': 'Computer repair, phone repair, CCTV installation, and technical services',
                'job_categories': [
                    'Computer Repair', 'Phone Repair', 'Network Installation', 
                    'CCTV Installation', 'Aircon Cleaning & Repair', 'Appliance Installation',
                    'Appliance Repair', 'Solar Panel Installation', 'Generator Repair'
                ]
            },
            'automotive': {
                'name': 'Automotive & Motorcycles',
                'icon': 'fas fa-car',
                'description': 'Auto repair, motorcycle services, detailing, and vehicle maintenance',
                'job_categories': [
                    'Auto Repair', 'Auto Detailing', 'Tire Services', 'Motorcycle Repair',
                    'Auto Body Work', 'Auto Painting', 'Auto Electrical', 'Car Washing', 'Bike Repair'
                ]
            },
            'personal_care': {
                'name': 'Personal Care & Beauty',
                'icon': 'fas fa-cut',
                'description': 'Hair cutting, beauty services, massage therapy, and personal care',
                'job_categories': [
                    'Hair Cutting', 'Barbering', 'Massage Therapy', 'Beauty Services',
                    'Nail Services', 'Makeup Artist'
                ]
            },
            'food_services': {
                'name': 'Food Services',
                'icon': 'fas fa-utensils',
                'description': 'Cooking, catering, baking, and food service work',
                'job_categories': [
                    'Cook', 'Baker', 'Food Vendor', 'Bartender', 'Waiter/Waitress', 'Catering'
                ]
            },
            'education': {
                'name': 'Education & Tutoring',
                'icon': 'fas fa-graduation-cap',
                'description': 'Tutoring, teaching, training, and educational services',
                'job_categories': [
                    'Academic Tutoring', 'Music Lessons', 'Language Lessons', 
                    'Skills Training', 'Driving Instructor'
                ]
            },
            'delivery': {
                'name': 'Delivery & Transportation',
                'icon': 'fas fa-truck',
                'description': 'Delivery services, courier, driving, and transportation',
                'job_categories': [
                    'Delivery Services', 'Courier Services', 'Food Delivery', 'Grocery Delivery',
                    'Errand Services', 'Driver Services', 'Tricycle Driver', 'Pedicab Driver',
                    'Trucking Services', 'Pabili Services'
                ]
            },
            'professional': {
                'name': 'Professional Services',
                'icon': 'fas fa-briefcase',
                'description': 'Accounting, legal, design, development, and professional work',
                'job_categories': [
                    'Accounting', 'Legal Services', 'Graphic Design', 'Web Development',
                    'Social Media Management', 'Content Writing', 'Translation Services',
                    'Virtual Assistant', 'Data Entry', 'Transcription Services', 
                    'Online Selling Assistant'
                ]
            },
            'care_services': {
                'name': 'Care Services',
                'icon': 'fas fa-hands-helping',
                'description': 'Childcare, elderly care, pet care, and caregiving services',
                'job_categories': [
                    'Childcare', 'Babysitting', 'Elderly Care', 'Pet Care', 'Pet Grooming',
                    'Pet Walking', 'Pet Sitting', 'Housekeeping', 'Nanny Services', 'Companion Care'
                ]
            },
            'maintenance': {
                'name': 'Maintenance & Repair',
                'icon': 'fas fa-wrench',
                'description': 'General maintenance, repairs, and handyman services',
                'job_categories': [
                    'General Maintenance', 'Door & Window Repair', 'Furniture Repair',
                    'Lock & Key Services', 'Refrigeration Repair', 'Pump Repair'
                ]
            },
            'manufacturing': {
                'name': 'Manufacturing & Industrial',
                'icon': 'fas fa-industry',
                'description': 'Factory work, warehouse, packaging, and industrial jobs',
                'job_categories': [
                    'Factory Work', 'Warehouse Work', 'Packaging Services',
                    'Quality Control', 'Machine Operation', 'Assembly Line Work'
                ]
            },
            'agriculture': {
                'name': 'Agriculture & Farming',
                'icon': 'fas fa-seedling',
                'description': 'Farm labor, crop harvesting, livestock, and agricultural work',
                'job_categories': [
                    'Farm Labor', 'Crop Harvesting', 'Livestock Care', 'Fishing Services',
                    'Agricultural Equipment Operation'
                ]
            },
            'specialized': {
                'name': 'Specialized Services',
                'icon': 'fas fa-star',
                'description': 'Security, janitorial, and other specialized services',
                'job_categories': [
                    'Security Services', 'Janitorial Services', 'Septic Tank Cleaning',
                    'Waterproofing', 'Pool Maintenance', 'Elevator Maintenance',
                    'Shoe Repair', 'Tailoring & Sewing'
                ]
            },
            'gig_economy': {
                'name': 'Side Hustles & Gig Economy',
                'icon': 'fas fa-hand-holding-usd',
                'description': 'Event work, promotional jobs, and various gig economy opportunities',
                'job_categories': [
                    'Party Host/Entertainer', 'Event Staff', 'Event Planning', 'Promotional Model',
                    'Product Assembly', 'Gift Wrapping', 'Reselling/Buy & Sell',
                    'Online Shop Assistant', 'Queue Services (Pila)', 'Bill Payment Services',
                    'Document Processing', 'Printing Services', 'Photography', 'Videography'
                ]
            },
            'other': {
                'name': 'Other',
                'icon': 'fas fa-ellipsis-h',
                'description': 'Other miscellaneous jobs and services',
                'job_categories': ['Other', 'Others']
            }
        }
        
        created_count = 0
        updated_count = 0
        linked_count = 0
        
        for slug, data in categories_mapping.items():
            # Create or update general category
            general_cat, created = GeneralCategory.objects.get_or_create(
                slug=slug,
                defaults={
                    'name': data['name'],
                    'description': data['description'],
                    'icon': data['icon']
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'  ✓ Created: {data["name"]}'))
            else:
                # Update existing
                general_cat.name = data['name']
                general_cat.description = data['description']
                general_cat.icon = data['icon']
                general_cat.save()
                updated_count += 1
                self.stdout.write(self.style.WARNING(f'  - Updated: {data["name"]}'))
            
            # Link job categories to general category
            for job_cat_name in data['job_categories']:
                try:
                    job_cat = JobCategory.objects.get(name=job_cat_name)
                    if job_cat.general_category != general_cat:
                        job_cat.general_category = general_cat
                        job_cat.save()
                        linked_count += 1
                        self.stdout.write(f'    → Linked: {job_cat_name}')
                except JobCategory.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f'    ⚠ Job category not found: {job_cat_name}'))
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'Summary:'))
        self.stdout.write(self.style.SUCCESS(f'  Created: {created_count} general categories'))
        self.stdout.write(self.style.WARNING(f'  Updated: {updated_count} general categories'))
        self.stdout.write(self.style.SUCCESS(f'  Linked: {linked_count} job categories'))
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('General categories populated successfully!'))
