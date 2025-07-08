import paramiko
import time
import sys

# --- Configuration ---
# IMPORTANT: Replace these placeholders with your actual device details.
# For better security in a production environment, consider using environment variables
# or a secure configuration management system for credentials.
HOSTNAME = '10.73.70.25'
USERNAME = 'admin'
PASSWORD = 'your_ssh_password'  # The password for the 'admin' user to SSH into the device
SUDO_PASSWORD = 'your_sudo_password' # The password required by 'sudo su' to elevate privileges
COMMAND_TO_RUN = 'k get service -A |grep redis' # The command to execute after becoming root

def ssh_and_run_command(hostname, username, password, sudo_password, command_to_execute):
    """
    Connects to an SSH host, elevates to superuser, and runs a command.

    Args:
        hostname (str): The IP address or hostname of the device.
        username (str): The SSH username.
        password (str): The SSH password for the given username.
        sudo_password (str): The password for the 'sudo su' command.
        command_to_execute (str): The command to run after gaining root privileges.
    """
    client = paramiko.SSHClient()
    # Automatically add the server's host key (use with caution in production,
    # prefer to verify host keys manually or via known_hosts file)
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        print(f"Attempting to connect to {hostname} as user '{username}'...")
        # Establish the SSH connection
        client.connect(hostname, username=username, password=password, timeout=15)
        print("Successfully connected via SSH.")

        # Invoke an interactive shell. This is necessary for 'sudo su' as it requires
        # a pseudo-terminal to prompt for a password.
        shell = client.invoke_shell()
        print("Interactive shell invoked.")

        # Give the shell a moment to present the initial prompt
        time.sleep(1)
        # Read any initial output from the shell
        output = shell.recv(4096).decode('utf-8')
        print(f"\n--- Initial Shell Output ---\n{output.strip()}\n----------------------------")

        # Send the 'sudo su' command to switch to root user
        print("Sending 'sudo su' command to elevate privileges...")
        shell.send('sudo su\n')

        # Wait for the prompt for the sudo password
        time.sleep(1)
        output = shell.recv(4096).decode('utf-8')
        print(f"\n--- Output after 'sudo su' ---\n{output.strip()}\n------------------------------")

        # Check if the password prompt is present
        if '[sudo] password for admin:' in output or 'Password:' in output:
            print("Password prompt detected. Sending sudo password...")
            shell.send(f'{sudo_password}\n') # Send the sudo password followed by a newline
            time.sleep(1) # Give time for the password to be processed
            output = shell.recv(4096).decode('utf-8')
            print(f"\n--- Output after sending sudo password ---\n{output.strip()}\n------------------------------------------")
            if 'Sorry, try again.' in output:
                print("Sudo password incorrect. Exiting.", file=sys.stderr)
                return
            elif 'incorrect password attempt' in output:
                print("Sudo password incorrect. Exiting.", file=sys.stderr)
                return
            else:
                print("Sudo password accepted (or no explicit failure message).")
        else:
            print("Sudo password prompt not explicitly found, assuming already root or no password needed for sudo.")

        # Send the desired command after becoming root
        print(f"Sending command as root: '{command_to_execute}'...")
        shell.send(f'{command_to_execute}\n')

        # Wait for the command to execute and capture its output
        # Adjust sleep time based on how long your command typically takes to run
        time.sleep(5)
        
        # Read all available output from the shell until no more data is ready
        command_output = ""
        while shell.recv_ready():
            command_output += shell.recv(4096).decode('utf-8')
        
        print(f"\n--- Output of '{command_to_execute}' ---\n{command_output.strip()}\n------------------------------------------")

    except paramiko.AuthenticationException:
        print("Authentication failed. Please check your SSH username, SSH password, and sudo password.", file=sys.stderr)
    except paramiko.SSHException as e:
        print(f"SSH connection or command execution error: {e}", file=sys.stderr)
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
    finally:
        if client:
            client.close()
            print("SSH connection closed.")

if __name__ == "__main__":
    ssh_and_run_command(HOSTNAME, USERNAME, PASSWORD, SUDO_PASSWORD, COMMAND_TO_RUN)
