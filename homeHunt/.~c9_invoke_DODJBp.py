import re
import uuid
import datetime
import json
from decimal import Decimal
from django.conf import settings
from django.contrib import messages
from django.http import HttpResponse
from django.http import JsonResponse
from .dynamo_helper import DynamoHelper
from .lambda_helper import LambdaHelper
from .cognito_helper import SimpleCognito
from .s3bucket_helper import S3BucketHelper
from botocore.exceptions import ClientError
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_protect
from home_hunt_error_pkg.validators import Validator
from home_hunt_error_pkg.exceptions import ValidationError
from home_hunt_error_pkg.aws_errors import AWSErrorHandler

@csrf_protect
def signingup( request ):
    """This function handles the user signup, and passes the user details to aws cognito for authentication"""
    context = { 'username': '', 'email': '', 'phone': '', 'errors': {} }
    if request.method == 'POST':
        username = request.POST.get( 'username', '' ).strip()
        email = request.POST.get( 'email', '' ).strip()
        phone = request.POST.get( 'phone', '' ).strip()
        password1 = request.POST.get( 'password1', '' )
        password2 = request.POST.get( 'password2', '' )

        # Updating context with form values
        context.update( { 'username': username, 'email': email, 'phone': phone } )

        try:
            Validator.validate_required_fields(request.POST, ['username', 'email', 'phone', 'password1', 'password2'])
            Validator.validate_email(email)
            Validator.validate_phone_number(phone)
            Validator.validate_passwords(password1, password2)

            # Cognito user signup/registration
            cognito = SimpleCognito()
            response = cognito.sign_up( username, password1, email, phone )
            return redirect( 'confirm', username = username )
        except ValidationError as ve:
            context['errors']['general'] = ve.message
        except ClientError as ce:
            ve = AWSErrorHandler.handle_cognito_errors(ce)
            context['errors']['general'] = ve.message
        except Exception as e:
            context['errors']['general'] = str(e)
            
        return render( request, 'signup.html', context )

    return render( request, 'signup.html', context )

@csrf_protect
def confirm_signup( request, username ):
    """This function handles the user confirm_signup, and uses the provided user details while signup from aws cognito and authenticates the user"""
    context = { 'username': username, 'errors': {} }
    if request.method == 'POST':
        username = request.POST.get( 'username' )
        code = request.POST.get( 'code' )
        context['username'] = username

        try:
            # Validate input
            Validator.validate_required_fields(
                {'username': username, 'code': code}, 
                ['username', 'code']
            )
            
            cognito = SimpleCognito()
            response = cognito.confirm_sign_up( username, code )
            return redirect( 'login' )

        except ValidationError as ve:
            context['errors']['general'] = ve.message

        except ClientError as ce:
            aws_errors = AWSErrorHandler.handle_cognito_errors(ce)
            context['errors']['general'] = aws_errors.message
            
        except Exception as e:
            context['errors']['general'] = str( e )

    return render( request, 'confirmation.html', context )

@csrf_protect
def login_view( request ):
    """This function handles the user login, it uses the aws cognito for authorization"""
    context = { 'username': '', 'errors': {} }
    if request.method == 'POST':
        username = request.POST.get( 'username', '' ).strip()
        password = request.POST.get( 'password', '' ).strip()

        try:
            # Validate input fields
            Validator.validate_required_fields({'username': username, 'password': password}, ['username', 'password'])

            cognito = SimpleCognito()
            response = cognito.login(username, password)
            # Store tokens in session
            request.session['access_token'] = response['AuthenticationResult']['AccessToken']
            request.session['refresh_token'] = response['AuthenticationResult']['RefreshToken']
            return redirect( 'home', username=username )
            
        except ValidationError as ve:
            context['errors']['general'] = ve.message

        except ClientError as ce:
            ve = AWSErrorHandler.handle_cognito_errors(ce)
            context['errors']['general'] = ve.message
        
        except Exception as e:
            context['errors']['general'] = str(e)
            
    return render(request, 'login.html', context)
    
def home_page(request, username):
    
    # Only get first 100 items for initial load
    dynamo = DynamoHelper()
    properties = dynamo.get_initial_properties(limit=100)
    context = {
        'username': username,
        'properties': properties
    }
    
    return render(request, 'home.html', context)
    
@csrf_protect
def place_ad(request, username):
    """This function validates the property details and stores the property details and images in dynamo db and s3 bucket respectively"""
    context = {'username': username}
    if request.method == 'POST':
        try:
            # prepare dynamo db object and validate id same propertry exists
            dynamo_helper = DynamoHelper()
            postal_code = request.POST.get('postal_code')
            if dynamo_helper.get_eir_code(postal_code):
                raise Exception("Property with same EIR code is already present, EIR code cannot be same.")

            images = request.FILES.getlist('images')
            # Process images
            s3_helper = S3BucketHelper()
            image_urls = []
            
            for img in images:
                try:
                    # Validate file type
                    if not img.name.lower().endswith(('.png', '.jpg', '.jpeg')):
                        context['error'] = f'Invalid file type: {img.name}. Allowed formats: PNG, JPG, JPEG'
                        return render(request, 'place_ad.html', context)
                    
                    # Upload to S3
                    filename = f"{username}/{uuid.uuid4()}_{img.name}"
                    image_url = s3_helper.upload_file(img, filename)
                    if not image_url:
                        raise Exception(f"S3 upload failed for {img.name}")
                    image_urls.append(image_url)
                
                except Exception as e:
                    context['error'] = f"Image upload error: {str(e)}"
                    return render(request, 'place_ad.html', context)

            # Prepare DynamoDB data
            property_id = str(uuid.uuid4())  # Unique ID for each property

            try:
                property_data = {
                    'id': property_id,
                    'address': request.POST.get('address'),
                    'county': request.POST.get('county'),
                    'postal_code': postal_code,
                    'bedrooms': int(request.POST.get('bedrooms')),
                    'bathrooms': int(request.POST.get('bathrooms')),
                    'property_type': request.POST.get('property_type'),
                    'listing_type': request.POST.get('listing_type'),
                    'price': Decimal(request.POST.get('price')),
                    'owner_name': request.POST.get('owner_name'),
                    'username': username,
                    'status': request.POST.get('property_status'),
                    'images': image_urls,
                    'owner_email': request.POST.get('owner_email'),
                    'owner_phone': request.POST.get('owner_phone'),
                    'created_at': datetime.datetime.now().isoformat()
                }
                    
            except ValueError as e:
                context['error'] = f"Invalid data format: {str(e)}"
                return render(request, 'place_ad.html/'+username, context)

            # Save to DynamoDB
            try:
                if dynamo_helper.save_property(property_data):
                    messages.success(request, "Property Ad listed successfully!! 🎉🎉, "
                                                +"check MyListings to modify property details or Rent/Sell to view listed ad.")
                    return redirect('place_ad', username=username)  # Redirect to same page
                else:
                    raise Exception("Failed to save property to database")
                    
            except Exception as e:
                context['error'] = f"Database error: {str(e)}"
                return render(request, 'place_ad.html', context)

        except Exception as e:
            context['error'] = f"{str(e)}"
            return render(request, 'place_ad.html', context)

    return render(request, 'place_ad.html', context)
    

def listings(request, username, listing_type):
    """This function handles to display different templates like buy, rent, place ad, my listings and my bookings based on user selection"""
    context = {'username': username, 'listing_type': listing_type}
    dynamo_helper = DynamoHelper()
    if listing_type == 'rent':
        properties = dynamo_helper.get_rent_listed_properties()
    elif listing_type == 'sell':
        properties = dynamo_helper.get_sell_listed_properties()
    elif listing_type == 'mylistings':
        properties = dynamo_helper.get_my_listings(username)
    else:
        listing_type = 'mybookings'
        properties = dynamo_helper.get_booked_property_details(username)
        
    if properties:    
        context['properties'] = properties
    return render(request, 'property_listings.html', context)

    
def property_details(request, action_type, username, property_id):
    """This function displays the property details of the specific property selected by the user"""
    dynamo_helper = DynamoHelper()
    properties = dynamo_helper.get_property_details( property_id )
    context = {'username': username, 'action_type': action_type, 'property': properties}
    return render(request, 'property_details.html', context)

@csrf_protect
def book_viewing(request, username, property_id):
    """This function displays the book viewing page for the property to user and invokes lambda function 
    which further access sns and sqs services to send booking email notifications"""
    owner_details  = {}
    view_details   = {}
    booked_details = {}
    
    hours               = list(range(9, 19))
    dynamo_helper       = DynamoHelper()
    booking_details     = dynamo_helper.get_booking_details( property_id )
    property_details    = dynamo_helper.get_property_details( property_id )
    
    for slot in booking_details:
        date = slot['booking_date']
        time = slot['time_slot']
        if date not in booked_details:
            booked_details[date] = []
        booked_details[date].append(time)

    # Calculate date range
    today       = datetime.datetime.now().date()
    min_date    = today + datetime.timedelta(days = 1)
    max_date    = today + datetime.timedelta(days = 14)

    context = {
        'property': property,
        'min_date': min_date.strftime('%Y-%m-%d'),
        'max_date': max_date.strftime('%Y-%m-%d'),
        'booked_slots': booked_details,
        'username': username,
        'hours': hours
    }

    if request.method == 'POST':
        try:
            dynamo_helper = DynamoHelper()
            booking_details = {
                    'id': str(uuid.uuid4()),
                    'property_id': property_id,
                    'booking_date': request.POST.get('booking_date'),
                    'time_slot': request.POST.get('selected_time'),
                    'viewer_name': request.POST.get('viewer_name'),
                    'viewer_email': request.POST.get('viewer_email'),
                    'viewer_phone': request.POST.get('viewer_phone'),
                    'booking_owner_name': username,
            }

            # Prepare and send notifications
            try:
                lambda_helper = LambdaHelper()
                lambda_payload = {
                    'property_id': property_id,
                    'property_address': f"{property_details['address']}, {property_details['county']}, {property_details['postal_code']}",
                    'owner_name': property_details['owner_name'],
                    'owner_email': property_details['owner_email'],
                    'owner_phone': property_details['owner_phone'],
                    'viewer_name': request.POST.get('viewer_name'),
                    'viewer_email': request.POST.get('viewer_email'),
                    'viewer_phone': request.POST.get('viewer_phone'),
                    'booking_date': request.POST.get('booking_date'),
                    'time_slot': request.POST.get('selected_time')
                }

                response = lambda_helper.invoke_notification( lambda_payload )
                
                if response['statusCode'] == 200:
                    messages.success(request, "Booking request submitted! Check your email for subscription confirmation.")
                    if dynamo_helper.save_booking_details( booking_details ):
                        messages.success(request, "Booking confirmed successfully!! 🎉🎉")
                        properties = dynamo_helper.get_property_details( property_id )
                        return redirect('book-viewing', username=username, property_id=property_id)
                    else:
                        raise Exception("Failed to save property to database")
                else: 
                    raise Exception("Failed to save property to database")
    
            except Exception as e:
                context['error'] = f"Database error: {str(e)}"
                return render(request, 'book_viewing.html', context)

        except Exception as e:
            context['error'] = f"Database error: {str(e)}"
            return render(request, 'book_viewing.html', context)

    return render(request, 'book_viewing.html', context)

def edit_property_details(request, username, property_id):
    """This function handles the updation of property details and store the updated property details in Dynamo Db table and S3 bucket respectively"""
    dynamo_helper = DynamoHelper()
    properties = dynamo_helper.get_property_details(property_id)
    context = {'username': username, 'property': properties}

    if request.method == 'POST':
        try:
            property_data = {
                'owner_name': request.POST.get('owner_name'),
                'address': request.POST.get('address'),
                'county': request.POST.get('county'),
                'postal_code': request.POST.get('postal_code'),
                'bedrooms': int(request.POST.get('bedrooms')),
                'bathrooms': int(request.POST.get('bathrooms')),
                'property_type': request.POST.get('property_type'),
                'listing_type': request.POST.get('listing_type'),
                'property_status': request.POST.get('property_status'),
                'price': Decimal(request.POST.get('price')),
                'owner_email': request.POST.get('owner_email'),
                'owner_phone': request.POST.get('owner_phone'),
                'updated_at': datetime.datetime.now().isoformat()
            }
        except ValueError as e:
            context['error'] = f"Invalid data format: {str(e)}"
            return render(request, 'edit_property.html', context)
            
        try:
            dynamo_helper = DynamoHelper()
            if dynamo_helper.update_property( property_id, property_data ):
                messages.success(request, "Property details updated successfully!! 🎉🎉")
                properties = dynamo_helper.get_property_details( property_id )
                return redirect('edit_property_details', username=username, property_id=property_id)
            else:
                raise Exception("Failed to save property to database")
                
        except Exception as e:
            context['error'] = f"Database error: {str(e)}"
            return render(request, 'edit_property.html', context)

    return render(request, 'edit_property.html', context)

def delete_property(request, username, property_id):
    """This function handles the property details deletion from dynamo db"""
    try:
        dynamo_helper = DynamoHelper()
        if dynamo_helper.delete_property( property_id ):
            return redirect('listings', username=username, listing_type='mylistings')
        else:
            raise Exception("Failed to save property to database")
            
    except Exception as e:
        properties = dynamo_helper.get_property_details(property_id)
        context = {'username': username, 'property': properties}
        context['error'] = f"Database error: {str(e)}"
        return render(request, 'edit_property.html', context)
    return render(request, 'edit_property.html', context)
    
def logout_user(request, username):
    """This function handles the user logout from the system using aws cognito"""
    try:
        cognito = SimpleCognito()
        response = cognito.logout(request.session['access_token'], request.session['refresh_token'], username)
        if response:
            return redirect( 'login' )
    except Exception as e:
        dynamo = DynamoHelper()
        properties = dynamo.get_initial_properties(limit=100)
        context = {
            'username': username,
            'properties': properties,
            'error': {str(e)}
        }
        return render(request, 'home.html', context )
    