import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import reset_queries, connection
from courses.models import Course, CourseMember, CourseContent

# ── Helper ──────────────────────────────────────────────
def print_query_count(label):
    print(f"\n{'='*50}")
    print(f"{label}: {len(connection.queries)} queries")
    print(f"{'='*50}")

# ── Setup: aktifkan query logging ───────────────────────
from django.conf import settings
settings.DEBUG = True

# ════════════════════════════════════════════════════════
# 1. N+1 PROBLEM (BURUK)
# ════════════════════════════════════════════════════════
print("\n\n>>> DEMO 1: N+1 Problem (tanpa optimasi)")
reset_queries()

courses = Course.objects.all()
for course in courses:
    print(f"  Course: {course.name} | Pengajar: {course.teacher.username}")

print_query_count("N+1 Problem")
print("  ⚠️  Setiap course butuh 1 query tambahan untuk ambil teacher!")

# ════════════════════════════════════════════════════════
# 2. SELECT_RELATED (FIX N+1 untuk ForeignKey)
# ════════════════════════════════════════════════════════
print("\n\n>>> DEMO 2: select_related (ForeignKey optimization)")
reset_queries()

courses = Course.objects.select_related('teacher').all()
for course in courses:
    print(f"  Course: {course.name} | Pengajar: {course.teacher.username}")

print_query_count("select_related")
print("  ✅ Hanya 1 query dengan JOIN!")

# ════════════════════════════════════════════════════════
# 3. PREFETCH_RELATED (untuk ManyToMany / reverse FK)
# ════════════════════════════════════════════════════════
print("\n\n>>> DEMO 3: prefetch_related (ManyToMany optimization)")
reset_queries()

courses = Course.objects.prefetch_related('coursemember_set__user_id').all()
for course in courses:
    members = course.coursemember_set.all()
    print(f"  {course.name}: {members.count()} member")

print_query_count("prefetch_related")
print("  ✅ Hanya 2-3 queries untuk semua data!")

# ════════════════════════════════════════════════════════
# 4. ONLY & DEFER (ambil kolom tertentu saja)
# ════════════════════════════════════════════════════════
print("\n\n>>> DEMO 4: only() - ambil kolom tertentu")
reset_queries()

courses = Course.objects.only('name', 'price')
for course in courses:
    print(f"  {course.name}: Rp {course.price}")

print_query_count("only()")
print("  ✅ Lebih efisien, tidak ambil kolom yang tidak perlu!")

# ════════════════════════════════════════════════════════
# 5. ANNOTATE (agregasi di database)
# ════════════════════════════════════════════════════════
print("\n\n>>> DEMO 5: annotate() - hitung member di DB")
reset_queries()

from django.db.models import Count, Avg
courses = Course.objects.annotate(
    member_count=Count('coursemember')
).order_by('-member_count')

for course in courses:
    print(f"  {course.name}: {course.member_count} member")

print_query_count("annotate()")
print("  ✅ Agregasi dilakukan di database, bukan Python!")

print("\n\n=== SUMMARY PERBANDINGAN ===")
print("  N+1 Problem     : 1 query per object = BURUK")
print("  select_related  : 1 JOIN query       = BAGUS untuk FK")
print("  prefetch_related: 2 queries          = BAGUS untuk M2M")
print("  only()/defer()  : kolom terbatas     = BAGUS untuk performa")
print("  annotate()      : agregasi di DB     = BAGUS untuk counting")
