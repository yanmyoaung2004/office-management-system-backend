"""Serializers for School Office Management API."""
from rest_framework import serializers
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import authenticate
from .models import (
    User, Major, Year, Semester, Intake, Student, Enquiry,
    FollowUpSession, DailyReport, ReportEnquiry, Dropout, Enrollment, Notification
)


# Auth
class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(write_only=True)
    password = serializers.CharField(
        style={'input_type': 'password'},
        write_only=True
    )

    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')

        if username and password:
            user = authenticate(request=self.context.get('request'),
                                username=username, password=password)
            if not user:
                raise serializers.ValidationError(
                    _('Unable to log in with provided credentials.'),
                    code='authorization'
                )
            
            if not user.is_active:
                raise serializers.ValidationError(
                    _('User account is disabled.'),
                    code='authorization'
                )
        else:
            raise serializers.ValidationError(
                _('Must include "username" and "password".'),
                code='authorization'
            )
        attrs['user'] = user
        return attrs

# User
class UserSerializer(serializers.ModelSerializer):
    fullName = serializers.CharField(source='full_name')

    class Meta:
        model = User
        fields = ['id', 'username', 'fullName', 'email', 'role', 'is_superuser']
        read_only_fields = ['id', 'username']


class UserDetailSerializer(serializers.ModelSerializer):
    # Mapping camelCase (Frontend) to snake_case (Backend)
    fullName = serializers.CharField(source='full_name')
    createdAt = serializers.DateTimeField(source='date_joined', read_only=True)
    # Note: 'last_login' only changes on login. 
    # For a real update timestamp, you'd need a field with auto_now=True.
    updatedAt = serializers.DateTimeField(source='last_login', read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'fullName', 
            'role', 'password', 'createdAt', 'updatedAt'
        ]
        extra_kwargs = {
            # password should be write-only so it's never sent back to the frontend
            'password': {'write_only': True, 'required': False},
            'id': {'read_only': True}
        }

    def update(self, instance, validated_data):
        # 1. Handle Password separately (must be hashed)
        password = validated_data.pop('password', None)
        if password:
            instance.set_password(password)

        # 2. Update all other fields automatically
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance

class UserCreateSerializer(serializers.ModelSerializer):
    fullName = serializers.CharField(source='full_name')
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ['username', 'password', 'fullName', 'email', 'role']

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError('Username already exists')
        return value

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            password=validated_data['password'],
            full_name=validated_data['full_name'],
            email=validated_data['email'],
            role=validated_data.get('role', 'staff')
        )
        return user


# Major, Year and Semester
class SemesterSerializer(serializers.ModelSerializer):
    semesterNumber = serializers.IntegerField(source='semester_number', allow_null=True, required=False)
    id = serializers.CharField(required=False) # Important for updates

    class Meta:
        model = Semester
        fields = ['id', 'semesterNumber', 'name']


class YearSerializer(serializers.ModelSerializer):
    semesters = SemesterSerializer(many=True, required=False)
    yearNumber = serializers.IntegerField(required=False, allow_null=True)
    id = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = Year
        fields = ['id', 'type', 'yearNumber', 'name', 'semesters']

    def validate(self, data):
        """Ensure FOUNDATION vs NORMAL year rules"""
        year_type = data.get('type')
        year_num = data.get('yearNumber')

        if year_type == 'FOUNDATION':
            if year_num is not None:
                raise serializers.ValidationError("Foundation year must have yearNumber = null")
        
        if year_type == 'NORMAL':
            if year_num is None:
                raise serializers.ValidationError("Normal year must have a valid yearNumber")
            
        return data



class MajorDetailSerializer(serializers.ModelSerializer):
    years = YearSerializer(many=True)
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)

    class Meta:
        model = Major
        fields = ['id', 'name', 'code', 'description', 'createdAt', 'years']

    def create(self, validated_data):
        years_data = validated_data.pop('years', [])
        major = Major.objects.create(**validated_data)

        for year_data in years_data:
            semesters_data = year_data.pop('semesters', [])
            year_obj = Year.objects.create(major=major, **year_data)

            for sem_data in semesters_data:
                Semester.objects.create(year=year_obj, **sem_data)

        return major
    @transaction.atomic
    def update(self, instance, validated_data):
        years_data = validated_data.pop('years', [])
        
        # 1. Update Major basic fields
        instance.name = validated_data.get('name', instance.name)
        instance.code = validated_data.get('code', instance.code)
        instance.description = validated_data.get('description', instance.description)
        instance.save()

        # 2. Track existing years to handle deletions
        existing_years = {y.id: y for y in instance.years.all()}
        incoming_year_ids = [y_data.get('id') for y_data in years_data if y_data.get('id')]

        # DELETE years not present in the PUT request
        for y_id, y_obj in list(existing_years.items()):
            if y_id not in incoming_year_ids:
                y_obj.delete()
                del existing_years[y_id]

        # 3. Process Years (Update or Create)
        for year_data in years_data:
            year_id = year_data.get('id')
            semesters_data = year_data.pop('semesters', []) # Extract semesters

            if year_id and year_id in existing_years:
                # Update existing year
                year_obj = existing_years[year_id]
                year_obj.name = year_data.get('name', year_obj.name)
                year_obj.type = year_data.get('type', year_obj.type)
                year_obj.yearNumber = year_data.get('yearNumber', year_obj.yearNumber)
                year_obj.save()
            else:
                # Create new year
                year_obj = Year.objects.create(major=instance, **year_data)

            # 4. Process Semesters within this year
            existing_sems = {s.id: s for s in year_obj.semesters.all()}
            incoming_sem_ids = [s_data.get('id') for s_data in semesters_data if s_data.get('id')]

            # DELETE removed semesters (Automatically clears Foundation years)
            for s_id, s_obj in list(existing_sems.items()):
                if s_id not in incoming_sem_ids:
                    s_obj.delete()
                    del existing_sems[s_id]

            # UPDATE or CREATE semesters
            for sem_data in semesters_data:
                sem_id = sem_data.get('id')
                # Map source back from 'semesterNumber' key
                sem_num = sem_data.get('semester_number') 
                sem_name = sem_data.get('name')

                if sem_id and sem_id in existing_sems:
                    sem_obj = existing_sems[sem_id]
                    sem_obj.name = sem_name
                    sem_obj.semester_number = sem_num
                    sem_obj.save()
                else:
                    Semester.objects.create(
                        year=year_obj,
                        semester_number=sem_num,
                        name=sem_name
                    )

        return instance
        
# Intake

class EnrollmentListSerializer(serializers.ModelSerializer):
    studentId = serializers.CharField(source='student.id')
    fullName = serializers.CharField(source='student.full_name')
    email = serializers.EmailField(source='student.email')
    studentPhone = serializers.CharField(source='student.student_phone_no')
    status = serializers.CharField()
    enrolledDate = serializers.DateField(source='enrolled_date')

    class Meta:
        model = Enrollment
        fields = [
            'id',
            'studentId',
            'fullName',
            'email',
            'studentPhone',
            'status',
            'enrolledDate',
        ]


class IntakeSemesterScheduleSerializer(serializers.Serializer):
    id = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    semester_id = serializers.CharField(max_length=20)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    def validate(self, data):
        if data['end_date'] <= data['start_date']:
            raise serializers.ValidationError("end_date must be after start_date")
        if not Semester.objects.filter(id=data['semester_id']).exists():
            raise serializers.ValidationError(f"Semester {data['semester_id']} does not exist")
        
        return data
    


class IntakeSerializer(serializers.ModelSerializer):
    majorId = serializers.PrimaryKeyRelatedField(
        source='major', queryset=Major.objects.all()
    )
    majorName = serializers.CharField(source='major.name', read_only=True)
    currentStatus = serializers.SerializerMethodField()
    currentSemId  = serializers.CharField(source='current_semester.id', read_only=True)
    semester_schedules = IntakeSemesterScheduleSerializer(many=True, read_only=True, source='scheduled_semesters')
    
    class Meta:
        model = Intake
        fields = [
            'id', 'code', 'majorId', 'majorName', 'year',
            'startDate', 'endDate', 'capacity', 'createdAt', 
            'currentStatus', 'currentSemId', 'enrollments',
            'semester_schedules'
        ]
        extra_kwargs = {
            'startDate': {'source': 'start_date'},
            'endDate': {'source': 'end_date'},
            'createdAt': {'source': 'created_at', 'read_only': True},
        }

    def get_currentStatus(self, obj):
        """Combines Year and Semester into one string."""
        if obj.current_semester:
            year_name = obj.current_semester.year.name if obj.current_semester.year else ""
            sem_name = obj.current_semester.name
            return f"{year_name} - {sem_name}"
        return "N/A"

class IntakeCreateSerializer(serializers.ModelSerializer):
    currentSemId = serializers.PrimaryKeyRelatedField(
        source='current_semester', 
        queryset=Semester.objects.all(),
        required=False,
        allow_null=True
    )
    majorId = serializers.PrimaryKeyRelatedField(
        source='major', 
        queryset=Major.objects.all()
    )
    startDate = serializers.DateField(source='start_date')
    endDate = serializers.DateField(source='end_date', required=False, allow_null=True)
    semester_schedules = IntakeSemesterScheduleSerializer(many=True, write_only=True)

    class Meta:
        model = Intake
        fields = ['code', 'majorId', 'year', 'startDate', 'endDate', 'capacity', 'currentSemId', 'semester_schedules']

    def create(self, validated_data):
        return super().create(validated_data)

# Student
class EnrollmentSerializer(serializers.ModelSerializer):
    student_id = serializers.PrimaryKeyRelatedField(
        queryset=Student.objects.all(), source='student'
    )
    intake_id = serializers.PrimaryKeyRelatedField(
        queryset=Intake.objects.all(), source='intake'
    )

    class Meta:
        model = Enrollment
        fields = [
            'id', 'student_id', 'intake_id', 'status', 'enrolled_date', 
            'scholar', 'registration_fee', 'first_installment_fee', 
            'nrc_copy', 'census_copy', 'passport_photo', 
            'education_certificate', 'remark'
        ]
        read_only_fields = ['id']


class StudentCreateSerializer(serializers.ModelSerializer):
    # We use the frontend keys as the variable names so 'validated_data' 
    # matches your JSON exactly.
    fullName = serializers.CharField(source='full_name')
    educationLevel = serializers.CharField(source='education_level')
    birthDate = serializers.DateField(source='birth_date')
    studentPhoneNo = serializers.CharField(source='student_phone_no')
    parentName = serializers.CharField(source='parent_name', required=False, allow_blank=True)
    parentPhoneNo = serializers.CharField(source='parent_phone_no', required=False, allow_blank=True)
    referralName = serializers.CharField(source='referral_name', required=False, allow_blank=True)
    # without 'source' to keep the keys exactly as they come from React.
    intakeId = serializers.PrimaryKeyRelatedField(queryset=Intake.objects.all())
    enrolledDate = serializers.DateField()
    status = serializers.CharField(default='Enrolled')
    scholar = serializers.BooleanField(default=False)
    registrationFee = serializers.BooleanField(default=False)
    firstInstallmentFee = serializers.BooleanField(default=False)
    nrcCopy = serializers.BooleanField(default=False)
    censusCopy = serializers.BooleanField(default=False)
    passportPhoto = serializers.BooleanField(default=False)
    educationCertificate = serializers.BooleanField(default=False)
    remark = serializers.CharField(required=False, allow_blank=True)
    street = serializers.CharField(required=True, allow_blank=False)
    city = serializers.CharField(required=True, allow_blank=False)
    region = serializers.CharField(required=True, allow_blank=False)

    class Meta:
        model = Student
        fields = [
            'fullName', 'educationLevel', 'gender', 'nrc', 'birthDate',
            'studentPhoneNo', 'parentName', 'parentPhoneNo', 'email',
            'referralName', 'street', 'city', 'region',
            'intakeId', 'enrolledDate', 'status', 
            'scholar', 'registrationFee', 'firstInstallmentFee',
            'nrcCopy', 'censusCopy', 'passportPhoto', 'educationCertificate', 'remark'
        ]

    def create(self, validated_data):
        # Extract the fields using the EXACT names defined above
        intake = validated_data.pop('intakeId')
        enrolled_date = validated_data.pop('enrolledDate') # Matches variable name
        status = validated_data.pop('status', 'Enrolled')
        scholar = validated_data.pop('scholar', False)
        remark = validated_data.pop('remark', '')
        
        # Extract checkboxes using CamelCase keys
        reg_fee = validated_data.pop('registrationFee', False)
        first_fee = validated_data.pop('firstInstallmentFee', False)
        nrc_c = validated_data.pop('nrcCopy', False)
        census_c = validated_data.pop('censusCopy', False)
        photo = validated_data.pop('passportPhoto', False)
        cert = validated_data.pop('educationCertificate', False)

        with transaction.atomic():
            # Create Student (validated_data now only contains Student fields 
            # like full_name, birth_date, etc. thanks to the 'source' mapping)
            student = Student.objects.create(**validated_data)

            # Create Enrollment
            Enrollment.objects.create(
                student=student,
                intake=intake,
                enrolled_date=enrolled_date,
                status=status,
                scholar=scholar,
                registration_fee=reg_fee,
                first_installment_fee=first_fee,
                nrc_copy=nrc_c,
                census_copy=census_c,
                passport_photo=photo,
                education_certificate=cert,
                remark=remark
            )

        return student


class StudentListSerializer(serializers.ModelSerializer):
    # Data from the related Student model
    studentId = serializers.ReadOnlyField(source='student.id')
    fullName = serializers.CharField(source='student.full_name', read_only=True)
    nrc = serializers.CharField(source='student.nrc', read_only=True)
    gender = serializers.CharField(source='student.gender', read_only=True)
    street = serializers.CharField(source='student.street', read_only=True)
    city = serializers.CharField(source='student.city', read_only=True)
    region = serializers.CharField(source='student.region', read_only=True)
    email = serializers.EmailField(source='student.email', read_only=True)
    studentPhoneNo = serializers.CharField(source='student.student_phone_no', read_only=True)
    educationLevel = serializers.CharField(source='student.education_level', read_only=True)
    birthDate = serializers.DateField(source='student.birth_date', read_only=True)
    parentName = serializers.CharField(source='student.parent_name', read_only=True)
    parentPhoneNo = serializers.CharField(source='student.parent_phone_no', read_only=True)
    referralName = serializers.CharField(source='student.referral_name', read_only=True)

    # Data from the related Intake model
    intakeId = serializers.ReadOnlyField(source='intake.id')
    intakeCode = serializers.CharField(source='intake.code', read_only=True)
    majorName = serializers.CharField(source='intake.major.name', read_only=True)
    
    # Data directly on the Enrollment model (Local fields)
    enrolledDate = serializers.DateField(source='enrolled_date')
    registrationFee = serializers.BooleanField(source='registration_fee')
    firstInstallmentFee = serializers.BooleanField(source='first_installment_fee')
    nrcCopy = serializers.BooleanField(source='nrc_copy')
    censusCopy = serializers.BooleanField(source='census_copy')
    passportPhoto = serializers.BooleanField(source='passport_photo')
    educationCertificate = serializers.BooleanField(source='education_certificate')
    
    currentStatus = serializers.SerializerMethodField()
    dropout = serializers.SerializerMethodField()

    class Meta:
        model = Enrollment
        fields = [
            'id', 'studentId', 'fullName', 'nrc', 'birthDate', 'gender', 'email', 
            'studentPhoneNo', 'educationLevel', 'majorName', 'parentName', 
            'parentPhoneNo', 'referralName', 'registrationFee', 'firstInstallmentFee',
            'intakeId', 'intakeCode', 'status', 'scholar', 'currentStatus',
            'enrolledDate', 'nrcCopy', 'censusCopy', 'passportPhoto', 
            'educationCertificate', 'remark', 'dropout', 'street', 'city', 'region'
        ]
    
    def get_dropout(self, obj):
        if hasattr(obj, 'dropout_record'):
            return {
                "intakeId": obj.intake.id,
                "reason": obj.dropout_record.reason,
                "remark": obj.dropout_record.remark
            }
        return None

    def get_currentStatus(self, obj):
        """Combines Year and Semester from the Intake related to this Enrollment."""
        intake = obj.intake
        if intake and intake.current_semester:
            year_name = intake.current_semester.year.name if intake.current_semester.year else ""
            sem_name = intake.current_semester.name
            return f"{year_name} - {sem_name}".strip(" - ")
        return "N/A"

class StudentDetailSerializer(StudentListSerializer):
    updatedAt = serializers.DateTimeField(source='updated_at')

    class Meta(StudentListSerializer.Meta):
        fields = StudentListSerializer.Meta.fields + ['updatedAt']

class StudentUpdateSerializer(serializers.ModelSerializer):
    # Student Fields
    fullName = serializers.CharField(source='student.full_name', required=False)
    street = serializers.CharField(source='student.street', required=False)
    city = serializers.CharField(source='student.city', required=False)
    region = serializers.CharField(source='student.region', required=False)
    studentPhoneNo = serializers.CharField(source='student.student_phone_no', required=False)
    parentPhoneNo = serializers.CharField(source='student.parent_phone_no', required=False)
    email = serializers.EmailField(source='student.email', required=False)
    educationLevel = serializers.CharField(source='student.education_level', required=False)
    birthDate = serializers.DateField(source='student.birth_date', required=False)
    nrc = serializers.CharField(source='student.nrc', required=False)
    parent_name = serializers.CharField(source='student.parent_name', required=False)
    referral_name = serializers.CharField(source='student.referral_name', required=False)
    gender = serializers.CharField(source='student.gender', required=False)
    
    # Enrollment Fields (Directly on the model now)
    nrcCopy = serializers.BooleanField(source='nrc_copy', required=False)
    censusCopy = serializers.BooleanField(source='census_copy', required=False)
    passportPhoto = serializers.BooleanField(source='passport_photo', required=False)
    educationCertificate = serializers.BooleanField(source='education_certificate', required=False)
    scholar = serializers.BooleanField(required=False)
    registration_fee = serializers.BooleanField(required=False)
    first_installment_fee = serializers.BooleanField(required=False)
    intakeId = serializers.PrimaryKeyRelatedField(source='intake', queryset=Intake.objects.all(), required=False)

    class Meta:
        model = Enrollment
        fields = [
            'fullName', 'email', 'studentPhoneNo', 'parentPhoneNo', 'street', 'city', 'region',
            'nrcCopy', 'censusCopy', 'passportPhoto', 'educationCertificate', 'gender',
            'remark', 'scholar', 'educationLevel', 'birthDate', 'nrc', 'parent_name', 'referral_name',
            'registration_fee', 'first_installment_fee', 'intakeId'

        ]

    @transaction.atomic
    def update(self, instance, validated_data):
        # 1. Handle nested Student data
        student_data = validated_data.pop('student', None)
        if student_data:
            student = instance.student
            for attr, value in student_data.items():
                setattr(student, attr, value)
            student.save()

        # 2. Handle Enrollment data (the remaining fields)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        return instance

# Enquiry
class FollowUpSessionSerializer(serializers.ModelSerializer):
    handledBy = serializers.CharField(source='handled_by')
    walkupFollowup = serializers.BooleanField(source='walkup_followup')
    enquiryId = serializers.CharField(source='enquiry_id', read_only=True)
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)

    class Meta:
        model = FollowUpSession
        fields = [
            'id', 'enquiryId', 'date', 'handledBy',
            'walkupFollowup', 'remark', 'createdAt'
        ]


class EnquiryListSerializer(serializers.ModelSerializer):
    desiredProgram = serializers.CharField(source='desired_program')
    studentName = serializers.CharField(source='student_name')
    educationLevel = serializers.CharField(source='education_level')
    studentContactNo = serializers.CharField(source='student_contact_no')
    parentName = serializers.CharField(source='parent_name')
    enquiryRemark = serializers.CharField(source='remark')
    parentContactNo = serializers.CharField(source='parent_contact_no')
    enquiryType = serializers.CharField(source='enquiry_type')
    sourceOfInformation = serializers.CharField(source='source_of_information')
    followUpCount = serializers.IntegerField(read_only=True)
    followUpSessions = FollowUpSessionSerializer(
        many=True, read_only=True, source='followups'
    )
    createdAt = serializers.DateTimeField(source='created_at')

    class Meta:
        model = Enquiry
        fields = [
            'id', 'date', 'desiredProgram', 'studentName', 'educationLevel',
            'studentContactNo', 'parentName', 'parentContactNo', 'address',
            'enquiryType', 'sourceOfInformation', 'remark', 'followUpCount',
            'followUpSessions', 'createdAt', 'enquiryRemark'
        ]


class EnquiryDetailSerializer(EnquiryListSerializer):
    followUpSessions = FollowUpSessionSerializer(
        many=True, read_only=True, source='followups'
    )
    updatedAt = serializers.DateTimeField(source='updated_at')

    class Meta(EnquiryListSerializer.Meta):
        fields = EnquiryListSerializer.Meta.fields + [
            'followUpSessions', 'updatedAt'
        ]


class EnquiryCreateSerializer(serializers.ModelSerializer):
    desiredProgram = serializers.CharField(source='desired_program')
    studentName = serializers.CharField(source='student_name')
    educationLevel = serializers.CharField(source='education_level')
    studentContactNo = serializers.CharField(source='student_contact_no')
    parentName = serializers.CharField(source='parent_name')
    parentContactNo = serializers.CharField(source='parent_contact_no')
    enquiryType = serializers.CharField(source='enquiry_type')
    sourceOfInformation = serializers.CharField(source='source_of_information')

    class Meta:
        model = Enquiry
        fields = [
            'date', 'desiredProgram', 'studentName', 'educationLevel',
            'studentContactNo', 'parentName', 'parentContactNo', 'address',
            'enquiryType', 'sourceOfInformation', 'remark'
        ]


class EnquiryUpdateSerializer(serializers.ModelSerializer):
    desiredProgram = serializers.CharField(source='desired_program', required=False)
    studentContactNo = serializers.CharField(
        source='student_contact_no', required=False
    )
    parentContactNo = serializers.CharField(
        source='parent_contact_no', required=False
    )

    class Meta:
        model = Enquiry
        fields = ['desiredProgram', 'studentContactNo', 'parentContactNo', 'address', 'remark']


# Follow-up
class FollowUpCreateSerializer(serializers.ModelSerializer):
    handledBy = serializers.CharField(source='handled_by')
    walkupFollowup = serializers.BooleanField(
        source='walkup_followup', default=False, required=False
    )
    remark = serializers.CharField(allow_blank=True, default='')

    class Meta:
        model = FollowUpSession
        fields = ['date', 'handledBy', 'walkupFollowup', 'remark']

    def create(self, validated_data):
        enquiry = validated_data.pop('enquiry', None)
        if not enquiry:
            raise serializers.ValidationError('Enquiry is required')
        return FollowUpSession.objects.create(enquiry=enquiry, **validated_data)


class FollowUpUpdateSerializer(serializers.ModelSerializer):
    handledBy = serializers.CharField(source='handled_by', required=False)
    walkupFollowup = serializers.BooleanField(source='walkup_followup', required=False)

    class Meta:
        model = FollowUpSession
        fields = ['date', 'handledBy', 'walkupFollowup', 'remark']


# Report
class ReportEnquirySerializer(serializers.ModelSerializer):
    enquiryId = serializers.CharField(source='enquiry_id')
    studentName = serializers.CharField(
        source='enquiry.student_name', read_only=True
    )

    class Meta:
        model = ReportEnquiry
        fields = ['enquiryId', 'studentName', 'action']


class ReportListSerializer(serializers.ModelSerializer):
    userId = serializers.CharField(source='user_id')
    userName = serializers.CharField(source='user.full_name')
    enquiryCount = serializers.IntegerField(read_only=True)
    createdAt = serializers.DateTimeField(source='created_at')

    class Meta:
        model = DailyReport
        fields = ['id', 'userId', 'userName', 'date', 'activities', 'enquiryCount', 'createdAt']


class ReportDetailSerializer(ReportListSerializer):
    enquiriesHandled = serializers.SerializerMethodField()
    updatedAt = serializers.DateTimeField(source='updated_at')

    class Meta(ReportListSerializer.Meta):
        fields = ReportListSerializer.Meta.fields + ['enquiriesHandled', 'updatedAt']

    def get_enquiriesHandled(self, obj):
        return [
            {
                'enquiryId': re.enquiry_id,
                'studentName': re.enquiry.student_name,
                'action': re.action
            }
            for re in obj.report_enquiries.select_related('enquiry').all()
        ]


class ReportCreateSerializer(serializers.ModelSerializer):
    userId = serializers.PrimaryKeyRelatedField(
        source='user', queryset=User.objects.all()
    )
    enquiriesHandled = serializers.ListField(
        child=serializers.DictField(),
        write_only=True,
        required=False
    )

    class Meta:
        model = DailyReport
        fields = ['userId', 'date', 'activities', 'enquiriesHandled']

    def validate_activities(self, value):
        if len(value) < 10:
            raise serializers.ValidationError('Activities must be at least 10 characters')
        return value

    def create(self, validated_data):
        enquiries_data = validated_data.pop('enquiriesHandled', [])
        if DailyReport.objects.filter(
            user=validated_data['user'],
            date=validated_data['date']
        ).exists():
            raise serializers.ValidationError(
                'Report for this user and date already exists'
            )
        report = DailyReport.objects.create(**validated_data)
        for item in enquiries_data:
            ReportEnquiry.objects.create(
                report=report,
                enquiry_id=item['enquiryId'],
                action=item['action']
            )
        return report


class ReportUpdateSerializer(serializers.ModelSerializer):
    enquiriesHandled = serializers.ListField(
        child=serializers.DictField(),
        required=False
    )

    class Meta:
        model = DailyReport
        fields = ['activities', 'enquiriesHandled']

    def update(self, instance, validated_data):
        enquiries_data = validated_data.pop('enquiriesHandled', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if enquiries_data is not None:
            instance.report_enquiries.all().delete()
            for item in enquiries_data:
                ReportEnquiry.objects.create(
                    report=instance,
                    enquiry_id=item['enquiryId'],
                    action=item['action']
                )
        return instance


# Dropout
class DropoutSerializer(serializers.ModelSerializer):
    enrollmentId = serializers.PrimaryKeyRelatedField(
        source='enrollment',
        queryset=Enrollment.objects.all()
    )
    dropoutDate = serializers.DateField(source='dropout_date')
    followUpDate = serializers.DateField(source='followup_date')

    resultingStatus = serializers.ChoiceField(
        choices=['Dropout', 'Interrupted'],
        write_only=True
    )

    class Meta:
        model = Dropout
        fields = [
            'id',
            'enrollmentId',
            'dropoutDate',
            'followUpDate',
            'reason',
            'remark',
            'resultingStatus',
        ]
        read_only_fields = ['id']

    def create(self, validated_data):
        resulting_status = validated_data.pop('resultingStatus')
        with transaction.atomic():
            dropout = Dropout.objects.create(**validated_data)
            enrollment = dropout.enrollment
            enrollment.status = resulting_status
            enrollment.save(update_fields=['status'])
            
            return dropout


# Notification
class NotificationSerializer(serializers.ModelSerializer):

    studentName = serializers.SlugRelatedField(
        read_only=True,
        slug_field='full_name'
    )
    alertType = serializers.ReadOnlyField(source='alert_type')
    isRead = serializers.BooleanField(source='is_read')
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)

    class Meta:
        model = Notification
        fields = [
            'id', 'user', 'studentName', 'title', 
            'message', 'alertType', 'isRead', 'createdAt'
        ]
        read_only_fields = ['id', 'createdAt', 'user']


# chart
class MajorEnrollmentSerializer(serializers.Serializer):
    major = serializers.CharField(source='intake__major__name')
    totalEnrolled = serializers.IntegerField(source='total')

    