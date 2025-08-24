import yagmail

try:
    yag = yagmail.SMTP('dchakraborty088889@gmail.com', 'hdtx skcs calq ubdp')

    yag.send(
        to='d.chakraborty2727@gmail.com',
        subject='Test Email',
        contents='Hello! This is a test email 2 sent using yagmail and Gmail App Password.'
    )

    print("Email sent successfully!")

except Exception as e:
    print("Error occurred:")
    print(e)
