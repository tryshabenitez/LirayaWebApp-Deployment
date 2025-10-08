from django.db import models
from django.utils import timezone
from django.core.validators import RegexValidator

# Add this above your model classes
name_validator = RegexValidator(
    regex=r'^[A-Za-z\s\-\'\.]+$',
    message="Please enter a valid name."
)

middle_name_validator = RegexValidator(
    regex=r'^([A-Za-z\s\-\'\.]+|[Nn]/?[Aa])$',
    message="Please enter a valid middle name. Use 'N/A' if not applicable."
)

# Account Information Table
class AccountInformation(models.Model):
    account_id = models.AutoField(primary_key=True)
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=150, unique=True)
    password = models.CharField(max_length=255)
    first_name = models.CharField(max_length=50, validators=[name_validator])
    middle_name = models.CharField(max_length=50, null=True, blank=True, validators=[middle_name_validator])
    last_name = models.CharField(max_length=50, validators=[name_validator])
    birth_date = models.DateField()
    gender = models.CharField(max_length=10)
    contact_num = models.CharField(max_length=20)
    profile_picture = models.ImageField(upload_to='profile_pics/', null=True, blank=True)
    house_no = models.CharField(max_length=20)
    street_village = models.CharField(max_length=100)
    barangay = models.CharField(max_length=100)
    city_municipality = models.CharField(max_length=100)
    province = models.CharField(max_length=100)
    zipcode = models.CharField(max_length=10)
    state = models.CharField(max_length=100)

    def save(self, *args, **kwargs):
        if self.middle_name and self.middle_name.lower() == "n/a":
            self.middle_name = None
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.username
    
    class Meta:
        db_table = 'account_information'


# User Accounts Table
class UserAccounts(models.Model):
    role_id = models.AutoField(primary_key=True)
    account = models.ForeignKey(AccountInformation, on_delete=models.CASCADE)
    role = models.CharField(max_length=50)  # Admin, Assistant, etc.
    account_status = models.CharField(max_length=20)  # Active, Deactivated
    previous_status = models.CharField(max_length=20, null=True, blank=True) 

    # NEW FIELDS
    created_by = models.ForeignKey(
        AccountInformation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_useraccounts'
    )
    created_when = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    
    class Meta:
        db_table = 'user_accounts'

# Reset Password Table
class ResetPassword(models.Model):
    reset_id = models.AutoField(primary_key=True)
    account = models.ForeignKey(AccountInformation, on_delete=models.CASCADE)
    otp_code = models.CharField(max_length=10)
    is_used = models.BooleanField(default=False)
    is_cancelled = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'reset_password'

class Books(models.Model):
    book_id = models.AutoField(primary_key=True)
    account = models.ForeignKey(AccountInformation, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    author = models.CharField(max_length=500)
    co_author = models.CharField(max_length=500, null=True, blank=True)
    date_uploaded = models.DateField(auto_now_add=True)
    year_of_publication = models.IntegerField(null=True, blank=True)
    publisher = models.CharField(max_length=255, null=True, blank=True) 
    primary_keyword = models.TextField()  # renamed from 'keyword'
    book_cover = models.ImageField(upload_to='book_covers/', null=True, blank=True)
    book_type = models.CharField(max_length=50)
    scanned_type = models.CharField(max_length=50)
    scanned_content = models.TextField()
    shelf_category = models.CharField(max_length=50, default="Uncategorized")  # Or any default value you prefer
    is_archived = models.BooleanField(default=False)  

    
    
    class Meta:
        db_table = 'books'


class KeywordLog(models.Model):
    """One row per normalized search string (no book data here)."""
    keyword_id = models.AutoField(primary_key=True)
    user_keyword_search = models.CharField(max_length=255, unique=True, db_index=True)
    user_search_count = models.IntegerField(default=0)
    search_times = models.TextField(default="", blank=True)  # append timestamps, one per line

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "keyword_log"

    def __str__(self):
        return f"[{self.keyword_id}] {self.user_keyword_search} x{self.user_search_count}"


class BookViewLog(models.Model):
    """
    Aggregate counter per book_id. We increment book_count on each 'View Information' click.
    """
    view_id = models.AutoField(primary_key=True)
    book_id = models.IntegerField(db_index=True, unique=True)  # stores Books.book_id
    book_count = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)  # first time this book was viewed
    updated_at = models.DateTimeField(auto_now=True)      # last time we bumped the count

    class Meta:
        db_table = "bookview_log"

    def __str__(self):
        return f"book_id={self.book_id} count={self.book_count}"



