import yagmail

try:
    yag = yagmail.SMTP('dchakraborty088889@gmail.com', 'hdtx xxxx xxxx xxxx')

    yag.send(
        to='d.chakraborty2727@gmail.com',
        subject='Test Email',
        contents='Hello! This is a test email sent using yagmail and Gmail App Password.'
    )

    print("Email sent successfully!")

except Exception as e:
    print("Error occurred:")
    print(e)

