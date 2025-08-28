# 🏡 Property Booking Notification System using AWS Lambda, SNS, SQS & EventBridge

This project is a **serverless notification system** built on **AWS Lambda**, **SNS (Simple Notification Service)** and **SQS (Simple Queue Service)**. 
It automates the sending of property booking confirmation emails to both property owners and viewers — **only if they are subscribed** to the notification system. 
Otherwise, it queues the request, tracks the subscription, and follows up automatically.

---

## ✅ Key Objectives

- Automate booking confirmation notifications
- Ensure email subscription before sending messages
- Queue unsubscribed users and handle delayed confirmation
- Trigger retry logic using EventBridge for 10 minutes after the initial request

---

## 🧠 How It Works

### Booking Flow:
1. A user (viewer) books a property.
2. Booking data (viewer + owner + property info) is passed to the first Lambda function.
3. Lambda checks if both emails are subscribed to the SNS topic.
4. ✅ If **both are subscribed**, an email is sent via SNS immediately.
5. ❌ If **either is not subscribed**:
   - Sends them a **subscription email** via SNS.
   - Stores the booking info in an **SQS queue**.
   - Starts an **EventBridge rule** to retry every 1 minute for the next 10 minutes.

### Retry Flow:
6. A second Lambda function is triggered every 1 minute by **EventBridge**.
7. It checks the SQS queue and subscription status.
8. If both are now subscribed:
   - Sends booking confirmation via SNS.
   - Deletes the message from the SQS queue.
9. After 10 minutes, the EventBridge rule **disables itself** automatically.


---

## ⚙️ AWS Services Used

- **AWS Lambda** – Serverless function execution
- **Amazon SNS** – Subscription-based email delivery
- **Amazon SQS** – Delayed processing for unsubscribed users
- **Amazon EventBridge** – Scheduling reattempts every minute
- **IAM** – Permissions and secure execution
- **CloudWatch** – Logs and debugging


---

## 🎯 Use Case

This system is ideal for:

- Real estate booking platforms
- Appointment booking apps
- Any system requiring double confirmation via email before notification delivery

---

## 📦 What Makes This Project Interesting?

- ✅ Dynamically creates SNS topic and SQS queue
- ✅ Automatically sends subscription emails
- ✅ Event-driven retry mechanism (10-minute window)
- ✅ Completely serverless (no backend server needed)
- ✅ Easily extendable to include SES, SMS, or push notifications

---

## 🔐 Security Considerations

- All actions are controlled through IAM roles
- SNS only sends to confirmed subscriptions
- Lambda has permission to access only the required services

---

## 🛠️ Requirements

- Python 3.8+
- AWS CLI (configured)
- IAM roles with appropriate permissions

---

## 🧪 Testing

- Use mock booking data to trigger Lambda
- Check if the owner/viewer receives the subscription email
- Confirm subscription and verify retry logic
- Watch logs in **CloudWatch** for full trace

---
