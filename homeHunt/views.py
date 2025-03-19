import re
import uuid
import datetime
from decimal import Decimal
from django.conf import settings
from django.contrib import messages
from django.http import JsonResponse
from .dynamo_helper import DynamoHelper
from .lambda_helper import LambdaHelper
from .cognito_helper import SimpleCognito
from .s3bucket_helper import S3BucketHelper
from botocore.exceptions import ClientError
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_protect

@csrf_protect
def signingup( request ):
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
            # Basic Form validation
            errors = {}
            if not all( [ username, email, phone, password1, password2 ] ):
                errors['general'] = 'All fields are required'
            
            # Confirm Password validation
            if password1 != password2:
                errors['password2'] = 'Password and Confirm Password does not match'
                
            # Phone number validation
            if not re.match( r'^\+353\d{9}$', phone ):
                errors['phone'] = 'Phone must be in Irish format ( +353 followed by 9 digits, e.g. +353851234567 )'

            if errors:
                context['errors'] = errors
                return render( request, 'signup.html', context )

            # Cognito user signup/registration
            cognito = SimpleCognito()
            response = cognito.sign_up( username, password1, email, phone )
            return redirect( 'confirm', username = username )

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            
            # Mapping Cognito error codes to form fields
            error_mapping = {
                'UsernameExistsException': ( 'username', 'Username already exists' ),
                'InvalidPasswordException': ( 'password1', 'Password should be 8 characters long, contains at least 1 number,' 
                                                +'1 special character, 1 uppercase character and 1 lowercase character ( Ex. abc@123 )' ),
                'InvalidParameterException': ( 'email', 'Invalid email address' ),
                'CodeDeliveryFailureException': ( 'email', 'Failed to send verification code' ),
                'InvalidPhoneNumberException': ( 'phone', 'Invalid phone number format' ),
            }
            
            field, message = error_mapping.get( error_code, ( 'general', error_message ) )
            context['errors'][field] = message
            
        except Exception as e:
            context['errors']['general'] = str( e )
        return render( request, 'signup.html', context )

    return render( request, 'signup.html', context )

@csrf_protect
def confirm_signup( request, username ):
    context = { 'username': username, 'errors': {} }
    
    if request.method == 'POST':
        username = request.POST.get( 'username' )
        code = request.POST.get( 'code' )
        context['username'] = username

        try:
            cognito = SimpleCognito()
            response = cognito.confirm_sign_up( username, code )
            return redirect( 'login' )
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            error_mapping = {
                'CodeMismatchException': 'Invalid verification code',
                'ExpiredCodeException': 'Code has expired. Please request a new one.',
                'UserNotFoundException': 'User does not exist',
            }
            message = error_mapping.get( error_code, ( 'general', error_message ) )
            context['errors']['general'] = message
            
        except Exception as e:
            context['errors']['general'] = str( e )

    return render( request, 'confirmation.html', context )


def resend_code(request):
    if request.method == 'POST':
        cognito = SimpleCognito()
        try:
            response = cognito.client.resend_confirmation_code(
                ClientId=settings.AWS_COGNITO['APP_CLIENT_ID'],
                SecretHash=cognito._secret_hash(request.POST.get('username')),
                Username=request.POST.get('username')
            )
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
    return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)

@csrf_protect
def login_view( request ):
    context = { 'username': '', 'errors': {} }
    if request.method == 'POST':
        username = request.POST.get( 'username', '' ).strip()
        password = request.POST.get( 'password', '' ).strip()

        try:
            cognito = SimpleCognito()
            response = cognito.login(username, password)
            # Store tokens in session
            request.session['access_token'] = response['AuthenticationResult']['AccessToken']
            request.session['refresh_token'] = response['AuthenticationResult']['RefreshToken']
            return redirect( 'home', username=username )
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            error_mapping = {
                'NotAuthorizedException': 'Invalid username or password',
                'UserNotFoundException': 'User does not exist',
                'InvalidPasswordException': 'Password should be 8 characters long, Contains at least 1 number,' 
                                                +'Contains at least 1 special character, Contains at least 1 uppercase letter,' 
                                                +'Contains at least 1 lowercase letter',
            }
            message = error_mapping.get( error_code, ( 'general', error_message ) )
            context['errors']['general'] = message
        
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
    context = {'username': username, 'listing_type': listing_type}
    dynamo_helper = DynamoHelper()
    if listing_type == 'rent':
        properties = dynamo_helper.get_rent_listed_properties()
    elif listing_type == 'sell':
        properties = dynamo_helper.get_sell_listed_properties()
    else:
        properties = dynamo_helper.get_my_listings(username)
        
    if properties:    
        context['properties'] = properties
    return render(request, 'property_listings.html', context)

    
def property_details(request, action_type, username, property_id):
    dynamo_helper = DynamoHelper()
    properties = dynamo_helper.get_property_details( property_id )
    context = {'username': username, 'action_type': action_type, 'property': properties}
    return render(request, 'property_details.html', context)

@csrf_protect
def book_viewing(request, username, property_id):
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
            }

            # Prepare and send notifications
            try:
                lambda_helper = LambdaHelper()
                lambda_payload = {
                    'property_id': property_id,
                    'property_address': f"{property_details['address']} {property_details['county']} {property_details['postal_code']}",
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
                if response['ResponseMetadata']['HTTPStatusCode'] == 200:
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
                return render(request, 'book_viewing.html', {'error': str(e)})

        except Exception as e:
            context['error'] = f"Database error: {str(e)}"
            return render(request, 'book_viewing.html', context)

    return render(request, 'book_viewing.html', context)

def edit_property_details(request, username, property_id):
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
                return redirect('edit_property_details', username=username, property_id=property_id)  # Redirect to same page
            else:
                raise Exception("Failed to save property to database")
                
        except Exception as e:
            context['error'] = f"Database error: {str(e)}"
            return render(request, 'edit_property.html', context)

    return render(request, 'edit_property.html', context)

def delete_property(request, username, property_id):
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

def profile_view(request):
    username = request.GET.get('user', 'Guest')
    return render(request, 'profile.html', {'username': username})
    
    