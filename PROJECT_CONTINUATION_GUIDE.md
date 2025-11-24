# 🚀 Trabaholink Project Continuation Guide

## 📋 Quick Project Overview

**Project:** Trabaholink - Job Matching Platform  
**Tech Stack:** Django 5.1.6 + PostgreSQL + PostGIS + Docker  
**Server:** Ubuntu 24/7 via systemd + Ngrok  
**URL:** https://unoffered-unsatiated-roberto.ngrok-free.dev/  
**Theme:** Royal Blue (#1e3a8a) + Gold (#fbbf24)  
**Location:** `remote_trabaholink_download/`

---

## ⚠️ STRICT DEVELOPMENT RULES

### 🎨 Design Requirements (ALWAYS FOLLOW):
1. ✅ **Mobile-first AND PC-compatible** - Design for 320px → 1920px+
2. ✅ **DON'T create documentation files** unless prompted
3. ✅ **DON'T touch Capstone Project** in Desktop folder
4. ✅ **Prioritize bash commands** to solve issues
5. ✅ **Test results** and confirm issues resolved before ending
6. ✅ **Run local server if needed** to verify fixes
7. ✅ **Royal blue and gold color scheme** consistently

### 📱 Responsive Breakpoints:
- Mobile: 320px - 767px
- Tablet: 768px - 1023px  
- Desktop: 1024px - 1439px
- Large Desktop: 1440px - 1919px
- Extra Large: 1920px+

---

## 🎯 CURRENT PROJECT STATUS (Last Updated: 2024-11-25)

### ✅ Recently Completed Features (November 2024-2025):

#### 1. **Worker Availability Management System** ⭐ NEW
- **Location:** `jobs/views_availability.py`, `templates/jobs/manage_availability.html`
- **Features:**
  - Full UI for workers to set weekly schedules
  - Multiple time slots per day (supports split shifts)
  - Toggle days on/off for availability
  - Mobile-responsive with royal blue theme
  - Accessible from worker profile → "Manage Availability"
  - API endpoints: `/jobs/availability/manage/`, `/api/availability/get/`, `/api/availability/check-conflicts/`
- **Status:** ✅ FULLY DEPLOYED & WORKING

#### 2. **Availability Conflict Warnings** ⭐ NEW
- **Location:** `templates/jobs/contract_negotiation.html`, `jobs/views.py` (ContractNegotiationView)
- **Features:**
  - Automatic detection during contract negotiation
  - Yellow warning banner with icon
  - Lists up to 10 conflicting dates with reasons
  - Context-aware recommendations for workers and employers
  - Non-blocking (allows flexibility)
- **Status:** ✅ FULLY DEPLOYED & WORKING

#### 3. **Mobile Responsiveness Improvements** ⭐ ENHANCED
- **Navbar:** Font size 0.8125rem, weight 500, optimized for mobile
- **Login/Signup:** Input fields properly sized with `max-width: 100%` and `box-sizing: border-box`
- **Calendar:** Horizontal scroll (600px tablet, 560px mobile), edge-to-edge design
- **Profile Dropdown:** Full-width on mobile, properly visible
- **Status:** ✅ FULLY DEPLOYED & WORKING

#### 4. **Default Profile Avatars** ⭐ NEW
- **Location:** `static/images/default_avatar.svg`
- **Implementation:** Blue avatar SVG (royal blue gradient with person icon)
- **Applied to:**
  - Navbar profile button
  - Conversation list (messaging)
  - Profile detail pages
  - Job detail page (owner & applicants)
- **Status:** ✅ FULLY DEPLOYED & WORKING

#### 5. **Celery Background Tasks** ⭐ FIXED
- **PhilSys Auto-Verification:** Working with Playwright browser installed
- **Daily Schedule Reminders:** Running at 8:00 AM daily (Asia/Manila)
- **Redis Password:** Fixed in docker-compose.yml for all services
- **CV File Validator:** Handles missing files gracefully
- **Status:** ✅ FULLY DEPLOYED & WORKING

#### 6. **Media & File Management** ⭐ FIXED
- **Media Volume:** Synchronized between web and nginx containers
- **Profile Pictures:** Cleaned broken references, default avatars show correctly
- **Job Images:** Broken references removed from Jobs 11 & 12
- **Upload Permissions:** Fixed 775 permissions on /app/media
- **Status:** ✅ FULLY DEPLOYED & WORKING

#### 7. **Bug Fixes** ⭐ FIXED
- **Notification URL Errors:** Fixed "too many values to unpack" in `notifications/models.py`
- **View Profile Link:** Always shows own profile (not viewed user's profile)
- **Profile Edit 500 Error:** CV validator no longer crashes on missing files
- **Favicon:** Updated to .ico format, served correctly
- **Status:** ✅ FULLY DEPLOYED & WORKING

#### 8. **Privacy Settings System** ⭐ NEW (Nov 25, 2024)
- **Location:** `users/models.py` (PrivacySettings), `templates/users/privacy_settings.html`
- **Features:**
  - Profile visibility control (Public/Connections/Private)
  - Contact information privacy (hide email/phone)
  - Activity feed privacy settings
  - SEO indexing control (noindex meta tag)
  - Automatic enforcement on profile views
  - Owner can always view their own full profile
  - Admin override for moderation
- **Database:** OneToOne relationship with CustomUser, auto-creates with safe defaults
- **Status:** ✅ FULLY IMPLEMENTED, NEEDS MIGRATION ON PRODUCTION

#### 9. **Contract Time Fields** ⭐ ENHANCED (Nov 25, 2024)
- **Location:** `templates/jobs/contract_draft_form.html`, `contract_negotiation.html`
- **Features:**
  - Daily start_time and end_time input fields
  - HTML5 time pickers for better UX
  - Helpful tooltips and input guides
  - Integrated with availability conflict checking
  - Fields disabled when contract finalized
- **Status:** ✅ FULLY DEPLOYED & WORKING

#### 10. **Mobile Responsiveness Overhaul** ⭐ CRITICAL FIXES (Nov 24-25, 2024)
- **Login/Signup Pages:**
  - Fixed container padding (no more edge touching)
  - Proper input field sizing with `box-sizing: border-box`
  - Removed conflicting CSS from `mobile-fixes.css`
  - Touch targets meet 44x44px standard
- **Worker Calendar & Availability:**
  - Removed forced horizontal scroll (600px → 100%)
  - Touch targets increased to 44px minimum
  - Font sizes increased to 14px minimum (12px for labels)
  - Calendar/deadlines stack vertically on mobile
  - Day cells increased to 70-80px height
- **Worker Dashboard:**
  - Added "Manage My Availability" quick action button
  - Calendar and deadlines properly layout on mobile
  - Improved FullCalendar toolbar responsiveness
- **Status:** ✅ FULLY DEPLOYED & WORKING

#### 11. **Job Vacancy Management** ⭐ FIXED (Nov 24, 2024)
- **Issue:** Job deactivated after ONE contract completion (ignored remaining vacancies)
- **Fix:** Only deactivate when `job.vacancies == 0`
- **Location:** `jobs/views.py` (end_job function)
- **Behavior:**
  - Job stays active with remaining vacancies
  - Vacancy decrements on contract finalization (not acceptance)
  - Proper multi-position job support
- **Status:** ✅ FULLY DEPLOYED & WORKING

#### 12. **Notification Links** ⭐ FIXED (Nov 24, 2024)
- **Issue:** Messaging notification URL had redundant prefix (`/messaging/messaging/`)
- **Fix:** Changed from `messaging/<id>/` to `<id>/` in `messaging/urls.py`
- **Affected:** New message notifications
- **Status:** ✅ FULLY DEPLOYED & WORKING

#### 13. **Dashboard Role-Based Display** ⭐ FIXED (Nov 24, 2024)
- **Issue:** Dashboards shown based on activity, not user role
- **Fix:** Changed from `user.profile.role` to `user.role` (fields on CustomUser model)
- **Location:** `templates/mainpages/base.html`
- **Behavior:**
  - Worker role → Shows Worker Dashboard
  - Client role → Shows Employer Dashboard
  - Admin → Shows Admin Dashboard
- **Status:** ✅ FULLY DEPLOYED & WORKING

#### 14. **Cache Control & Logout Fix** ⭐ SECURITY (Nov 24, 2024)
- **Issue:** Back button showed cached authenticated pages after logout
- **Fix:** Added `NoCacheMiddleware` to prevent caching
- **Location:** `users/middleware.py`, `Trabaholink/settings.py`
- **Features:**
  - Cache-control headers on all authenticated pages
  - JavaScript pageshow event detection
  - Forces reload on back button navigation
  - Meta tags prevent browser caching
- **Status:** ✅ FULLY DEPLOYED & WORKING

#### 15. **Template Syntax Fixes** ⭐ CRITICAL (Nov 24, 2024)
- **manage_availability.html:**
  - Fixed `{% else %}` → `{% empty %}` in for loop
  - Added missing `{% endfor %}` tag
  - Fixed URL namespace: `users:profile` → `profile`
- **Status:** ✅ FULLY DEPLOYED & WORKING

---

## 🚀 PENDING DEPLOYMENT (Production Server)

### ⚠️ Critical - Requires Migration:

#### Privacy Settings System
```bash
# On production server:
cd /root/Trabaholink
git pull origin main
./dc.sh exec web python manage.py makemigrations users
./dc.sh exec web python manage.py migrate
./dc.sh restart web
```

**What it does:**
- Creates `PrivacySettings` table
- Auto-creates settings for existing users on first access
- Non-destructive migration (safe)

**After deployment:**
- Users can access `/users/privacy_settings/`
- Privacy enforcement active on all profile views
- Contact info hidden based on settings

---

## 📊 System Architecture

### WorkerAvailability Model
- **Location:** `jobs/models.py` (lines 622-733)
- **Purpose:** Manage worker's weekly working hours to prevent schedule conflicts
- **Fields:**
  - `worker` - ForeignKey to CustomUser
  - `day_of_week` - Integer (0=Monday, 6=Sunday)
  - `start_time` - TimeField
  - `end_time` - TimeField
  - `is_available` - BooleanField
  
- **Key Methods:**
  - `get_worker_availability(worker, day_of_week)` - Get availability schedule
  - `check_availability_for_contract(worker, dates, times)` - Validate contract schedule
  - `check_conflict_with_contract(contract)` - Check specific contract conflicts

### Contract Workflow Integration
- **Location:** `jobs/forms.py`
- **Enhanced Forms:**
  - **ContractForm.clean()** - Validates availability when editing contracts
  - **ContractDraftForm.clean()** - Validates during contract drafting
  
- **Validation Checks:**
  1. Date validation (end >= start)
  2. Time validation (end > start)
  3. Existing contract conflicts (shows up to 3)
  4. Worker availability conflicts (shows up to 5)
  5. Detailed error messages with dates/times

---

## 🔧 DEPLOYMENT INFORMATION

### Server Deployment Commands:
```bash
# Standard deployment flow
cd /root/Trabaholink
git pull origin main
./dc.sh exec web python manage.py makemigrations jobs
./dc.sh exec web python manage.py migrate
./dc.sh restart web
./dc.sh ps

# One-liner for quick deployment
cd /root/Trabaholink && git pull origin main && ./dc.sh exec web python manage.py makemigrations jobs && ./dc.sh exec web python manage.py migrate && ./dc.sh restart web && ./dc.sh ps
```

### Useful Commands:
```bash
# Watch logs
./dc.sh logs web -f

# Django shell
./dc.sh exec web python manage.py shell

# Container shell
./dc.sh exec web bash

# Check status
./dc.sh ps
```

### DC.sh Wrapper:
`dc.sh` = `docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.production`

---

## 📁 KEY FILE LOCATIONS

### Templates:
```
remote_trabaholink_download/templates/
├── messaging/
│   ├── conversation_detail_new.html    # Main chat interface
│   └── conversation_list.html           # Search function
├── jobs/
│   ├── worker_dashboard_new.html        # Worker dashboard
│   ├── employer_dashboard_new.html      # Employer dashboard
│   └── components/
│       └── worker_calendar.html         # Calendar component
├── users/
│   └── profile_detail.html              # Profile edit icon
└── mainpages/
    └── base.html                        # Navbar logo
```

### Backend:
```
remote_trabaholink_download/
├── jobs/
│   ├── models.py          # Job, Contract, WorkerAvailability models
│   ├── forms.py           # ContractForm, ContractDraftForm with validation
│   ├── views.py           # Views logic
│   ├── urls.py            # URL routing
│   └── admin.py           # Admin panel configuration
├── messaging/
│   └── views.py           # Message handling & word filtering
├── admin_dashboard/
│   └── moderation_utils.py  # Word filtering (500+ banned words)
└── users/
    ├── models.py          # CustomUser model
    └── views.py           # User management
```

### Configuration:
```
remote_trabaholink_download/
├── docker-compose.yml          # Base Docker config
├── docker-compose.prod.yml     # Production overrides
├── .env.production             # Production environment variables
├── Dockerfile                  # Container build instructions
├── requirements.txt            # Python dependencies
└── dc.sh                       # Docker compose wrapper
```

---

## 🐛 KNOWN ISSUES & PATTERNS

### Recurring Issues to Watch:
1. **Search function in "New Message" button**
   - Endpoint: `/reports/search/users/`
   - Console shows results but UI doesn't display
   - Latest fix: inline styles to force visibility
   - Status: ⚠️ Monitor for regression

2. **Mobile responsiveness**
   - Navbar logo positioning on mobile
   - Profile edit icon sizing on mobile
   - Elements not adjusting to screen size
   - Status: ⚠️ Test on each deployment

3. **Layout consistency**
   - Navbar differences between pages
   - Margin/padding inconsistencies
   - Container width on wider screens (1024px+)
   - Status: ⚠️ Verify across all pages

### Testing Checklist (Always Run):
- [ ] Mobile: Logo size, profile edit icon, search modal
- [ ] Desktop: Margins, sidebar positioning, responsive breakpoints
- [ ] Search: "New Message" → type → results display
- [ ] Word censoring: Send profanity → instant censoring
- [ ] Calendar: Horizontal scroll on mobile (280px+)
- [ ] Contracts: Create with conflicting schedule → shows error

---

## 🎯 NEXT TASKS (Prioritized)

### Immediate Tasks:
1. **Deploy current changes to server** ⏰
   - Run migration for WorkerAvailability model
   - Test contract validation with real data
   - Verify calendar responsiveness

### High Priority:
2. **Create Worker Availability Management UI** 🔥
   - Allow workers to set their weekly hours
   - Show current availability on worker dashboard
   - CRUD interface for availability slots

3. **Add Availability Warnings in Offer Creation** 🔥
   - Check availability when employer creates offer
   - Show warning if worker unavailable
   - Suggest alternative time slots

4. **Display Availability on Worker Profile** 🔥
   - Show worker's available hours to employers
   - Visual calendar showing open slots
   - "Request availability change" feature

### Medium Priority:
5. **Fix Search Function (Again)** ⚠️
   - Review conversation_list.html search modal
   - Ensure results display properly
   - Test on mobile and desktop

6. **Mobile Navbar Consistency**
   - Standardize logo size across pages
   - Fix profile edit icon on mobile
   - Test on actual mobile devices

### Low Priority / Future Enhancements:
7. **Availability Calendar View**
   - Weekly view showing all availability slots
   - Color-coded by contract status
   - Drag-and-drop to adjust times

8. **Smart Scheduling Suggestions**
   - AI-powered time slot recommendations
   - Based on worker availability patterns
   - Conflict-free scheduling assistant

9. **Availability Notifications**
   - Notify worker when offer conflicts with availability
   - Remind workers to set availability
   - Alert employers about schedule changes

---

## 💡 HELPFUL CODE PATTERNS

### Checking Worker Availability:
```python
from jobs.models import WorkerAvailability
from datetime import date, time

# Check if worker is available
result = WorkerAvailability.check_availability_for_contract(
    worker=user,
    start_date=date(2024, 1, 1),
    end_date=date(2024, 1, 31),
    start_time=time(9, 0),
    end_time=time(17, 0)
)

if result['available']:
    print("Worker is available!")
else:
    for conflict in result['conflicts']:
        print(f"{conflict['date']}: {conflict['reason']}")
```

### Pre-validating Job Offer:
```python
# Before accepting offer
offer = JobOffer.objects.get(pk=offer_id)
availability = offer.check_worker_availability()

if not availability['available']:
    messages.warning(request, availability['message'])
    return redirect('offer_detail', offer.pk)

# Accept offer if available
contract = offer.accept_offer()
```

### Form Validation (Automatic):
```python
# In view
if request.method == 'POST':
    form = ContractForm(request.POST, instance=contract)
    if form.is_valid():  # Availability checks run here automatically
        form.save()
        messages.success(request, 'Contract updated!')
    else:
        # form.errors contains availability conflicts
        messages.error(request, 'Please resolve schedule conflicts.')
```

---

## 📊 DATABASE SCHEMA (Key Models)

### WorkerAvailability:
```python
{
    'id': Primary Key,
    'worker': ForeignKey(CustomUser),
    'day_of_week': Integer (0-6),
    'start_time': Time,
    'end_time': Time,
    'is_available': Boolean,
    'created_at': DateTime,
    'updated_at': DateTime
}
```

### Contract:
```python
{
    'id': Primary Key,
    'job': ForeignKey(Job),
    'worker': ForeignKey(CustomUser),
    'client': ForeignKey(CustomUser),
    'status': String (Negotiation/Finalized/In Progress/etc.),
    'start_date': Date,
    'end_date': Date,
    'start_time': Time,  # Daily start time
    'end_time': Time,    # Daily end time
    'agreed_rate': Decimal,
    # ... other fields
}
```

---

## 🔍 DEBUGGING TIPS

### Common Issues:
1. **Migration errors:** Check if model changes conflict with existing data
2. **Form validation not working:** Ensure instance.worker exists
3. **Time parsing fails:** Check JobOffer.work_schedule format
4. **Calendar not scrolling:** Verify min-width and overflow-x styles

### Useful Django Shell Commands:
```python
# Check worker availability
from jobs.models import WorkerAvailability
from users.models import CustomUser
worker = CustomUser.objects.get(username='worker_name')
availability = WorkerAvailability.get_worker_availability(worker)
for slot in availability:
    print(f"{slot.get_day_of_week_display()}: {slot.start_time} - {slot.end_time}")

# Check contract conflicts
from jobs.models import Contract
contract = Contract.objects.get(pk=1)
conflicts = contract.check_time_conflict()
if conflicts:
    for c in conflicts:
        print(c)
```

---

## 🎨 DESIGN TOKENS

### Colors:
```css
/* Primary Colors */
--trabaholink-blue: #1e3a8a;      /* Royal Blue */
--trabaholink-dark-blue: #1e40af;
--trabaholink-gold: #fbbf24;      /* Gold accent */

/* Status Colors */
--success-color: #10b981;          /* Green */
--danger-color: #ef4444;           /* Red */
--warning-color: #f59e0b;          /* Orange */
--info-color: #3b82f6;             /* Blue */

/* Neutral Colors */
--text-dark: #1e293b;
--text-medium: #64748b;
--text-light: #94a3b8;
--bg-white: #ffffff;
--bg-light: #f8fafc;
--border-color: #e2e8f0;
```

### Gradients:
```css
--gradient-primary: linear-gradient(135deg, #1e3a8a, #1e40af);
--gradient-accent: linear-gradient(135deg, #fbbf24, #f59e0b);
```

### Shadows:
```css
--shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.05);
--shadow-md: 0 4px 6px rgba(0, 0, 0, 0.1);
--shadow-lg: 0 10px 15px rgba(0, 0, 0, 0.1);
--shadow-xl: 0 20px 25px rgba(0, 0, 0, 0.15);
```

---

## 📝 COMMIT MESSAGE CONVENTIONS

### Format:
```
<type>: <subject>

<body (optional)>
```

### Types:
- **Add:** New feature or file
- **Fix:** Bug fix
- **Update:** Modify existing feature
- **Remove:** Delete feature or file
- **Refactor:** Code restructuring
- **Style:** Formatting, CSS changes
- **Docs:** Documentation only
- **Test:** Testing related

### Examples:
```
Add: WorkerAvailability model for hour management

- Create model with day/time fields
- Add conflict detection methods
- Register in admin panel
```

```
Fix: Mobile calendar horizontal scroll

- Add calendar-grid-wrapper with overflow-x
- Set min-width 280px for mobile
- Add touch-friendly scrolling
```

---

## 🚀 QUICK START (Next Session)

### 1. Pull Latest Changes:
```bash
cd ~/remote_trabaholink_download
git status
git pull origin main
```

### 2. Check Recent Commits:
```bash
git log --oneline -10
```

### 3. Review Current Status:
```bash
# Read this file
cat PROJECT_CONTINUATION_GUIDE.md

# Check what needs deployment
git diff origin/main
```

### 4. Start Development:
- Review "NEXT TASKS" section above
- Check "KNOWN ISSUES" for anything that needs attention
- Follow "STRICT DEVELOPMENT RULES" for all changes
- Test on mobile and desktop before committing

---

## 📞 IMPORTANT REMINDERS

### Before Making Changes:
1. ✅ Check if issue already fixed in recent commits
2. ✅ Review similar files for consistent patterns
3. ✅ Test on multiple screen sizes
4. ✅ Follow mobile-first approach
5. ✅ Use royal blue + gold color scheme

### Before Committing:
1. ✅ Test the specific feature you changed
2. ✅ Run git status to see all changes
3. ✅ Write clear commit message
4. ✅ Don't commit documentation files (unless asked)
5. ✅ Push to main branch only

### Before Deploying:
1. ✅ Ensure all changes are committed and pushed
2. ✅ Create deployment command with migrations
3. ✅ Test on server after deployment
4. ✅ Check logs for errors
5. ✅ Verify feature works in production

---

## 🎓 PROJECT CONTEXT

### What TrabahoLink Does:
- **For Workers:** Find jobs, apply, negotiate contracts, manage availability
- **For Employers:** Post jobs, review applicants, create offers, hire workers
- **Platform:** Facilitates secure contracts, payments, reviews, and messaging

### Key Features:
- ✅ Job posting with geolocation
- ✅ Worker applications with PhilSys verification
- ✅ Contract negotiation workflow
- ✅ Real-time messaging with word moderation
- ✅ Calendar for tracking contracts
- ✅ Worker availability management (NEW)
- ✅ Schedule conflict prevention (NEW)
- ✅ Payment tracking and reviews

### Current Focus:
Building out the **Worker Availability System** to:
1. Let workers set their weekly working hours
2. Prevent double-booking conflicts
3. Help employers schedule effectively
4. Provide better work-life balance for workers

---

## 🔗 EXTERNAL RESOURCES

### Documentation:
- Django Docs: https://docs.djangoproject.com/en/5.1/
- PostgreSQL + PostGIS: https://postgis.net/documentation/
- Docker Compose: https://docs.docker.com/compose/

### Design Resources:
- Color Palette: Royal Blue (#1e3a8a) + Gold (#fbbf24)
- Icons: Bootstrap Icons (https://icons.getbootstrap.com/)
- Fonts: System fonts (optimized for performance)

### Server Info:
- Server OS: Ubuntu Server
- Server Location: 114.29.239.240
- Ngrok URL: https://unoffered-unsatiated-roberto.ngrok-free.dev/
- Services: web, db, redis, nginx, celery_worker, celery_beat

---

## ✅ FINAL CHECKLIST

Before starting next session:
- [ ] Read this guide completely
- [ ] Check git status and recent commits
- [ ] Review NEXT TASKS section
- [ ] Understand current WorkerAvailability implementation
- [ ] Remember: Mobile-first, Royal Blue + Gold, Test thoroughly

**Ready to continue? Start with the highest priority task in NEXT TASKS section!** 🚀

---

*Last Updated: December 2024*  
*Project Status: Active Development - Worker Availability Phase*  
*Git Branch: main*  
*Next Major Feature: Worker Availability Management UI*
