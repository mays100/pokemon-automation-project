import boto3
import paramiko
import time
import os

# --- פרטי תצורה לפריסה (חובה לעדכן!) ---
# שנה/י לאזור ה-AWS שבו אתה רוצה לפרוס (לדוגמה: "us-west-2" או "eu-central-1")
# וודא/י שזה בתוך מרכאות כפולות.
AWS_REGION = "us-west-2" 

# סוג מופע EC2 (מומלץ t2.micro לשכבת החינם)
# וודא/י שזה בתוך מרכאות כפולות.
INSTANCE_TYPE = "t2.micro" 

# !!! זה חובה! הדבק/י כאן את ה-AMI ID המדויק שקיבלת בשלב 1.3 (לדוגמה: "ami-0abcdef1234567890") !!!
# וודא/י שזה בתוך מרכאות כפולות.
AMI_ID = "ami-0361aec2a849b21f4" 

# שם צמד המפתחות שיצרת ב-AWS (שלב 1.2)
# וודא/י שזה בתוך מרכאות כפולות.
KEY_PAIR_NAME = "pokemon-app-key" 

# שם קבוצת האבטחה שתיווצר (אפשר להשאיר ככה)
# וודא/י שזה בתוך מרכאות כפולות.
SECURITY_GROUP_NAME = "pokemon-app-sg" 

# !!! חובה! שנה/י לכתובת ה-URL המלאה של הריפוזיטוריון שלך ב-GitHub !!!
# וודא/י שזה בתוך מרכאות כפולות.
REPO_URL = "https://github.com/mays100/pokemon-automation-project.git" 

# נתיב לקובץ המפתח הפרטי שלך (.pem).
# מניח שהוא באותה תיקייה כמו deploy_app.py.
# אם קובץ ה-.pem נמצא בתיקייה אחרת, שנה/י לנתיב המלא: לדוגמה: "C:/Users/YourUser/.ssh/pokemon-app-key.pem"
# וודא/י שזה בתוך מרכאות כפולות.
SSH_KEY_PATH = "pokemon-app-key.pem" 

# --- לקוחות Boto3 ---
ec2_client = boto3.client('ec2', region_name=AWS_REGION)

def create_security_group():
    """יוצר קבוצת אבטחה עם פתיחת פורטים ל-SSH (22)."""
    try:
        response = ec2_client.describe_security_groups(GroupNames=[SECURITY_GROUP_NAME])
        print(f"קבוצת האבטחה '{SECURITY_GROUP_NAME}' כבר קיימת. ID: {response['SecurityGroups'][0]['GroupId']}")
        return response['SecurityGroups'][0]['GroupId']
    except ec2_client.exceptions.ClientError as e:
        if "InvalidGroup.NotFound" in str(e):
            print(f"יוצר קבוצת אבטחה חדשה: '{SECURITY_GROUP_NAME}'...")
            sg_response = ec2_client.create_security_group(
                GroupName=SECURITY_GROUP_NAME,
                Description='Security group for Pokemon App Server'
            )
            security_group_id = sg_response['GroupId']
            # פותח פורט 22 (SSH) מכל מקום (לא מומלץ בפרודקשן!)
            ec2_client.authorize_security_group_ingress(
                GroupId=security_group_id,
                IpPermissions=[
                    {'IpProtocol': 'tcp',
                     'FromPort': 22,
                     'ToPort': 22,
                     'IpRanges': [{'CidrIp': '0.0.0.0/0'}]} 
                ]
            )
            print(f"קבוצת האבטחה נוצרה בהצלחה עם ID: {security_group_id}")
            return security_group_id
        else:
            raise

def create_ec2_instance(security_group_id):
    """יוצר מופע EC2 חדש."""
    print("יוצר מופע EC2 חדש...")
    instances = ec2_client.run_instances(
        ImageId=AMI_ID,
        MinCount=1,
        MaxCount=1,
        InstanceType=INSTANCE_TYPE,
        KeyName=KEY_PAIR_NAME,
        SecurityGroupIds=[security_group_id],
        TagSpecifications=[
            {
                'ResourceType': 'instance',
                'Tags': [
                    {'Key': 'Name', 'Value': 'PokemonAppServer'},
                    {'Key': 'Project', 'Value': 'PokemonAppDeployment'}
                ]
            },
        ]
    )
    instance_id = instances['Instances'][0]['InstanceId']
    print(f"מופע EC2 נוצר עם ID: {instance_id}. ממתין שיהיה במצב ריצה...")
    
    # המתן עד שהמופע יהיה במצב ריצה (running)
    ec2_client.get_waiter('instance_running').wait(InstanceIds=[instance_id])
    
    # קבל את ה-IP הציבורי של המופע
    response = ec2_client.describe_instances(InstanceIds=[instance_id])
    public_ip = response['Reservations'][0]['Instances'][0]['PublicIpAddress']
    print(f"מופע EC2 במצב ריצה. IP ציבורי: {public_ip}")
    return instance_id, public_ip

def install_app_via_ssh(public_ip):
    """מתחבר לשרת באמצעות SSH ומתקין את האפליקציה."""
    print(f"מתחבר לשרת {public_ip} באמצעות SSH ומתקין את האפליקציה...")
    
    # נתיב מוחלט לקובץ מפתח SSH
    ssh_key_full_path = os.path.expanduser(SSH_KEY_PATH)
    if not os.path.exists(ssh_key_full_path):
        raise FileNotFoundError(f"קובץ מפתח SSH לא נמצא בנתיב: {ssh_key_full_path}")

    # הגדר הרשאות מתאימות לקובץ מפתח SSH ב-Linux/macOS (לא נחוץ ב-Windows)
    if os.name == 'posix': 
        os.chmod(ssh_key_full_path, 0o400) 

    key = paramiko.RSAKey.from_private_key_file(ssh_key_full_path)
    
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    # נסה להתחבר מספר פעמים, כי לפעמים לוקח לשרת זמן לעלות
    max_retries = 15
    for i in range(max_retries):
        try:
            print(f"ניסיון התחברות SSH ({i+1}/{max_retries})...")
            client.connect(hostname=public_ip, username='ubuntu', pkey=key, timeout=10) 
            print("התחברות SSH הצליחה.")
            break
        except paramiko.AuthenticationException:
            raise Exception("שגיאת אימות SSH. וודא שהמפתח הנכון משויך ל-Key Pair ב-EC2.")
        except Exception as e:
            if i == max_retries - 1:
                raise Exception(f"נכשל להתחבר לשרת באמצעות SSH לאחר מספר ניסיונות: {e}")
            time.sleep(10) 
    else:
        raise Exception("נכשל להתחבר לשרת באמצעות SSH לאחר מספר ניסיונות.")

    # פקודות להתקנה:
    commands = [
        "sudo apt update -y",
        "sudo apt install -y python3 python3-pip git",
        f"git clone {REPO_URL} /home/ubuntu/pokemon-app",
        "pip3 install requests",
        "echo 'ברוך הבא לשרת הפוקימונים!' | sudo tee /etc/motd", # תיקון: הסירי את ה-\!\!\! אם היו
        "echo '------------------------------------' | sudo tee -a /etc/motd",
        "echo 'להפעלת האפליקציה: cd /home/ubuntu/pokemon-app && python3 main.py' | sudo tee -a /etc/motd",
        "echo 'לסיום ההתחברות: exit' | sudo tee -a /etc/motd",
        "echo '------------------------------------' | sudo tee -a /etc/motd",
        "python3 /home/ubuntu/pokemon-app/main.py <<< $'כן\nלא'" # אין צורך בפסיק אחרי הפקודה האחרונה ברשימה
    ]

    for command in commands:
        print(f"מבצע פקודה: {command}")
        stdin, stdout, stderr = client.exec_command(command)
        exit_status = stdout.channel.recv_exit_status()
        output = stdout.read().decode('utf-8')
        error = stderr.read().decode('utf-8')
        if exit_status != 0:
            print(f"שגיאה בפקודה '{command}': {error}")
            raise Exception(f"התקנה נכשלה בפקודה: {command}")
        else:
            print(f"הפקודה '{command}' הושלמה בהצלחה.")
            if output:
                print(output)

    client.close()
    print("האפליקציה הותקנה והוגדרה בהצלחה.")

def terminate_instance(instance_id):
    """מסיים את מופע ה-EC2."""
    print(f"מסיים מופע EC2 עם ID: {instance_id}...")
    ec2_client.terminate_instances(InstanceIds=[instance_id])
    ec2_client.get_waiter('instance_terminated').wait(InstanceIds=[instance_id])
    print(f"מופע EC2 {instance_id} הסתיים בהצלחה.")

def main_deployment():
    """הלוגיקה הראשית של תהליך הפריסה."""
    instance_id = None
    try:
        security_group_id = create_security_group()
        instance_id, public_ip = create_ec2_instance(security_group_id)

        print("ממתין 60 שניות נוספות לוודא שירותי SSH זמינים...")
        time.sleep(60) 

        install_app_via_ssh(public_ip)
        print(f"\n--- פריסה הושלמה בהצלחה! ---")
        print(f"התחבר לשרת באמצעות SSH: ssh -i {SSH_KEY_PATH} ubuntu@{public_ip}")
        print("לאחר ההתחברות, הסבר השימוש יופיע. בהצלחה!")

    except Exception as e:
        print(f"\n!!! אירעה שגיאה קריטית במהלך הפריסה: {e} !!!")
        if instance_id:
            try:
                print(f"מנסה לסיים את מופע ה-EC2 ({instance_id}) כדי למנוע חיובים...")
                terminate_instance(instance_id)
            except Exception as terminate_e:
                print(f"שגיאה בסיום המופע: {terminate_e}")
        print("אנא בדוק את הלוגים לפרטים נוספים.")

if __name__ == "__main__":
    main_deployment()