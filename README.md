## Project Overview
A full-stack photography portfolio application that allows me to showcase my work 
with an admin panel for managing uploads, collections, and image metadata. 
Built with FastAPI backend, deployed on Render with Cloudflare R2 for image storage.

**Live Site:** [elvinsalcedo.com](https://elvinsalcedo.com)

## Tech Stack
**Backend:** FastAPI, SQLAlchemy, Alembic, JWT Auth\
**Database:** PostgreSQL (Supabase)\
**Storage:** Cloudflare R2 (S3-compatible)\
**Deployment:** Render\
**Frontend:** Tailwind CSS, Vanilla JavaScript\

## Key Features
- Secure admin authentication with JWT
- Image processing pipeline (resize, optimize, EXIF handling)
- Cloudflare R2 integration for scalable image storage
- Database migrations with Alembic
- Duplicate detection via SHA256 hashing

## Architecture Decisions

### Three-Service Architecture
1. **AdminService** - Photo CRUD operations, validation
2. **PhotoService** - Image retrieval and database queries  
3. **UserService** - Authentication, JWT, password hashing

## Technical Challenges

### Challenge 1: Image Orientation (EXIF)
**Problem:** Images displayed with incorrect rotation after upload
**Solution:** Used PIL's `ImageOps.exif_transpose()` to respect EXIF orientation data
**Learning:** Discovered EXIF metadata and its impact on image rendering

### Challenge 2: Service Layer Architecture
**Problem:** Tightly coupled code made testing difficult
**Solution:** Refactored into service layers following Domain-Driven Design principles
**Resources:** "Architecture Patterns with Python", Arjan Codes, Reddit communities

### Challenge 3: Async Image Processing with R2
**Problem:** Mixing sync PIL operations with async boto3 uploads
**Solution:** introduced the AIOfiles library for asynchronous I/O operations

## Lessons Learned
- Importance of separation of concerns for testability
- Working with byte buffers and in-memory file processing
- JWT authentication without Flask-Login abstraction
- When to pivot deployment strategies (Vercel → Render)

## Future Enhancements
- [ ] Add user comments/feedback
- [ ] E-commerce integration for print sales
- [ ] Advanced search/filtering
- [ ] Analytics dashboard
