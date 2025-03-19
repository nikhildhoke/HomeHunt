import boto3
import botocore.exceptions
from django.conf import settings
from boto3.dynamodb.conditions import Key, Attr

class DynamoHelper:
    def __init__(self):
        self._refresh_dynamodb()
        
    def _refresh_dynamodb(self):
        self.dynamodb = boto3.resource(
            'dynamodb',
            region_name = settings.AWS_REGION
        )
        self.tables = {
            'properties': self.dynamodb.Table( settings.DYNAMO_TABLE_NAME_1 ),
            'bookings': self.dynamodb.Table( settings.DYNAMO_TABLE_NAME_2 )
        }
        

    def get_initial_properties(self, limit=100):
        try:
            response = self.tables['properties'].scan(
                Limit=limit,
            )
            return response.get('Items', [])
        except Exception as e:
            print(f"Error fetching properties: {e}")
            return []

    def save_property(self, property_data):
        try:
            # First attempt to save the property
            response = self.tables['properties'].put_item( Item = property_data )
            if response['ResponseMetadata']['HTTPStatusCode'] != 200:
                raise Exception(f"DynamoDB error: { response['ResponseMetadata'] }")
            return True
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                # Table doesn't exist - create it
                self._create_table()
                # Retry the operation after table creation
                return self.save_property(property_data)
            raise Exception(f"DynamoDB Error: {str(e)}")
        except Exception as e:
            raise Exception(f"DynamoDB Error: {str(e)}")

    def _create_table(self):
        """Create the properties table if it doesn't exist"""
        client = self.dynamodb.meta.client
        try:
            table = client.create_table(
                TableName='cpp-properties',
                KeySchema=[
                    {
                        'AttributeName': 'id',
                        'KeyType': 'HASH'
                    }
                ],
                AttributeDefinitions=[
                    {
                        'AttributeName': 'id',
                        'AttributeType': 'S'
                    }
                ],
                ProvisionedThroughput={
                    'ReadCapacityUnits': 5,
                    'WriteCapacityUnits': 5
                }
            )
            # Wait for table to be created
            waiter = client.get_waiter('table_exists')
            waiter.wait(TableName='cpp-properties')
            print("Table 'cpp-properties' created successfully")
            
            # Refresh the table reference
            self._refresh_dynamodb()
            
        except client.exceptions.ResourceInUseException:
            # Table already exists (race condition)
            pass
        except Exception as e:
            raise Exception(f"Failed to create table: {str(e)}")
            
    def get_eir_code(self, postal_code):
        try:
            response = self.tables['properties'].scan(
                FilterExpression = Attr('postal_code').eq(postal_code)
            )
            return bool(response['Items'])
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == 'ExpiredTokenException':
                self._refresh_dynamodb()
                return self.get_eir_code(postal_code)
            elif e.response['Error']['Code'] == 'ResourceNotFoundException':
                return False
            else:
                raise Exception(f"Postal Code Error: {str(e)}")
        except Exception as e:
            raise Exception(f"Postal Code Error: {str(e)}")
        return False
        
    def get_rent_listed_properties(self):
        try:
            response = self.tables['properties'].scan(
                FilterExpression = Attr('listing_type').eq('rent')
            )
            properties = response.get('Items', [])
            return properties
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == 'ExpiredTokenException':
                # Refresh credentials and retry
                self._refresh_dynamodb()
                return self.get_rent_listed_properties()
            elif e.response['Error']['Code'] == 'ResourceNotFoundException':
                return []
            else:
                raise Exception(f"Code Error: {str(e)}")
            return []
        except Exception as e:
            raise Exception(f"Data not available: {str(e)}")
        return []
        
    def get_sell_listed_properties(self):
        try:
            response = self.tables['properties'].scan(
                FilterExpression = Attr('listing_type').eq('sell')
            )
            properties = response.get('Items', [])
            return properties
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == 'ExpiredTokenException':
                self._refresh_dynamodb()
                return self.get_sell_listed_properties()
            elif e.response['Error']['Code'] == 'ResourceNotFoundException':
                return []
            else:
                raise Exception(f"Code Error: {str(e)}")
            return []
        except Exception as e:
            raise Exception(f"Data not available: {str(e)}")
        return []
        
    def get_my_listings(self, username):
        try:
            response = self.tables['properties'].scan(
                FilterExpression = Attr('username').eq(username)
            )
            properties = response.get('Items', [])
            return properties
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == 'ExpiredTokenException':
                self._refresh_dynamodb()
                return self.get_my_listings( username )
            elif e.response['Error']['Code'] == 'ResourceNotFoundException':
                return False
            else:
                raise Exception(f"Code Error: {str(e)}")
            return []
        except Exception as e:
            raise Exception(f"Data not available: {str(e)}")
        return []
        
    def get_property_details(self, property_id):
        try:
            response = self.tables['properties'].scan(
                FilterExpression = Attr('id').eq(property_id)
            )
            properties = response.get('Items', [])
            return properties[0]
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == 'ExpiredTokenException':
                self._refresh_dynamodb()
                return self.get_property_details( property_id )
            raise Exception(f"Code Error: {str(e)}")
        except Exception as e:
            raise Exception(f"Data not available: {str(e)}")
        return []
        
    def update_property(self, property_id, property_data):
        try:
            response = self.tables['properties'].update_item(
                        Key={'id': property_id},
                        UpdateExpression="""
                            SET owner_name = :on, 
                                address = :a, 
                                county = :c, 
                                postal_code = :pc, 
                                bedrooms = :bdr, 
                                bathrooms = :bth, 
                                property_type = :pt, 
                                listing_type = :lt, 
                                property_status = :ps, 
                                price = :p, 
                                owner_email = :oe, 
                                owner_phone = :op                        
                        
                        """,
                        ExpressionAttributeValues={
                            ':on': property_data['owner_name'],
                            ':a': property_data['address'],
                            ':c': property_data['county'],
                            ':pc': property_data['postal_code'],
                            ':bdr': property_data['bedrooms'],
                            ':bth': property_data['bathrooms'],
                            ':pt': property_data['property_type'],
                            ':lt': property_data['listing_type'],
                            ':ps': property_data['property_status'],
                            ':p': property_data['price'],
                            ':oe': property_data['owner_email'],
                            ':op': property_data['owner_phone']
                        }
                    )
            if response['ResponseMetadata']['HTTPStatusCode'] == 200:
                return True
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == 'ExpiredTokenException':
                self._refresh_dynamodb()
                return self.update_property( property_id, property_data )
            raise Exception(f"Database Error: {str(e)}")
        except Exception as e:
            raise Exception(f"Database Error: {str(e)}")
        return False
        
    def delete_property(self, property_id):
        try:
            response = self.tables['properties'].delete_item(
                Key={
                        'id': property_id,
                }
            )
            if response['ResponseMetadata']['HTTPStatusCode'] != 200:
                raise Exception(f"DynamoDB error: { response['ResponseMetadata'] }")
            return True
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                return self.delete_property( property_id )
            raise Exception(f"DynamoDB Error: {str(e)}")
        except Exception as e:
            raise Exception(f"DynamoDB Error: {str(e)}")
            
    def get_booking_details(self, property_id):
        try:
            response = self.tables['bookings'].scan(
                FilterExpression = Attr('property_id').eq( property_id )
            )
            properties = response.get('Items', [])
            return properties
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == 'ExpiredTokenException':
                self._refresh_dynamodb()
                return self.get_booking_details( property_id )
            elif e.response['Error']['Code'] == 'ResourceNotFoundException':
                return []
            else:
                raise Exception(f"Code Error: {str(e)}")
                return []
        except Exception as e:
            raise Exception(f"Data not available: {str(e)}")
        return []
        
    def save_booking_details( self, booking_details ):
        try:
            response = self.tables['bookings'].put_item( Item = booking_details )
            if response['ResponseMetadata']['HTTPStatusCode'] != 200:
                raise Exception(f"DynamoDB error: { response['ResponseMetadata'] }")
            return True
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                
                self.create_bookings_table()
                return self.save_booking_details( booking_details )
            raise Exception(f"DynamoDB Error: {str(e)}")
        except Exception as e:
            raise Exception(f"DynamoDB Error: {str(e)}")
        
    def create_bookings_table( self ):
        client = self.dynamodb.meta.client
        try:
            table = client.create_table(
                TableName='cpp-bookings',
                KeySchema=[
                    {
                        'AttributeName': 'id',
                        'KeyType': 'HASH'
                    }
                ],
                AttributeDefinitions=[
                    {
                        'AttributeName': 'id',
                        'AttributeType': 'S'
                    }
                ],
                ProvisionedThroughput={
                    'ReadCapacityUnits': 10,
                    'WriteCapacityUnits': 10
                }
            )
            
            waiter = client.get_waiter('table_exists')
            waiter.wait(TableName='cpp-bookings')
            print("Table 'cpp-bookings' created successfully")
            
            self._refresh_dynamodb()
            
        except client.exceptions.ResourceInUseException:
            pass
        except Exception as e:
            raise Exception(f"Failed to create table: {str(e)}")