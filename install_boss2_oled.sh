#!/bin/bash
HOSTNAME="$(uname -n)"
if [ $HOSTNAME == "ropieeexl" ]
then
	ropieeeflag=2
elif [ $HOSTNAME == "ropieee" ] 
then
	ropieeeflag=1
else
	ropieeeflag=0
fi

#HOSTNAME="$(sudo hostname)"
ver_1=$(sudo python --version 2>&1)
IFS=' ' read -r -a array <<< "$ver_1"
IFS='.' read -r -a ver <<< "${array[1]}"
a=3
b=$(echo "${ver[0]}")
filename=/etc/rc.local
if [ $HOSTNAME == "moode" ]
then
	if [ $b -lt $a ]
	then
		echo "******************************************"
		echo "******************************************"
		echo "****                                  ****"
		echo "****              MOODE               ****"
		echo "****                                  ****"
		echo "******************************************"
		echo "******************************************"
		sudo apt-get -y update 
		sudo apt-get -y install python-pip
		sudo apt-get -y install python-smbus 
		sudo apt-get -y install python-pil 
		#sudo apt-get -y install python-netifaces 
		sudo raspi-config nonint do_i2c 0 
		while read line
		do
			if [ "$line" == "boss2flag=1" ]
			then
				flag=1
			fi
		done < $filename
		if [ "$flag" == "1" ]
		then
			echo "already installed"
			exit 0
		else
			sudo sed -i "`wc -l < /etc/rc.local`i\\boss2flag=1\\" /etc/rc.local
			sudo sed -i "`wc -l < /etc/rc.local`i\\sudo python /opt/boss2_oled/boss2_oled.py &\\" /etc/rc.local
			echo "******************************************"
			echo "***      Successfully Installed        ***"
			echo "******************************************"
			sleep 5
			sudo reboot
		fi

	else
		#sudo apt-get -y update 
		#sudo apt-get -y install python3-pip
		#sudo apt-get -y install python3-smbus 
		#sudo apt-get -y install python3-pil 
                echo "PYTHON greater version"
                echo "PYTHON version 2.7 or below required"
	fi
fi
if [ $HOSTNAME == "volumio" ]
then
        if [ $b -lt $a ]
        then
                echo "******************************************"
                echo "******************************************"
                echo "****                                  ****"
                echo "****             VOLUMIO              ****"
                echo "****                                  ****"
                echo "******************************************"
                echo "******************************************"
                sudo apt-get -y update
                sudo apt-get -y install python-pip
                sudo apt-get -y install python-smbus
                sudo apt-get -y install python-pil
		sudo apt-get -y install python-dev
		#sudo apt-get -y install python-netifaces 
		sudo pip install RPi.GPIO==0.7.0
                while read line
                do
                        if [ "$line" == "boss2flag=1" ]
                        then
                                flag=1
                        fi
                done < $filename
                if [ "$flag" == "1" ]
                then
                        echo "already installed"
                        exit 0
                else
                        sudo sed -i "`wc -l < /etc/rc.local`i\\boss2flag=1\\" /etc/rc.local
                        sudo sed -i "`wc -l < /etc/rc.local`i\\sudo python /opt/boss2_oled/boss2_oled.py &\\" /etc/rc.local
			echo "******************************************"
			echo "***      Successfully Installed        ***"
			echo "******************************************"
			sleep 5
                        reboot
                fi

        else
                echo "PYTHON greater version"
                echo "PYTHON version 2.7 or below required"
        fi
fi
if [ $HOSTNAME == "DietPi" ]
then
        if [ $b -lt $a ]
        then

                echo "******************************************"
                echo "******************************************"
                echo "****                                  ****"
                echo "****             DIETPI               ****"
                echo "****                                  ****"
                echo "******************************************"
                echo "******************************************"
                sudo apt-get -y update
                sudo apt-get -y install python-rpi.gpio
                sudo apt-get -y install python-pip
                sudo apt-get -y install python-smbus
                sudo apt-get -y install python-pil
		sudo apt-get -y install raspi-config
		sudo apt-get -y install i2c-tools
		sleep 2
		sudo raspi-config nonint do_i2c 0 
		#sudo apt-get -y install python-netifaces 
                sudo cp /opt/boss2_oled/boss2oled.service /etc/systemd/system/
                sudo systemctl enable boss2oled.service
                #sudo /boot/dietpi/dietpi-software install 72
                echo "******************************************"
                echo "***      Successfully Installed        ***"
                echo "******************************************"
                sleep 5
                reboot

        else
                echo "PYTHON greater version"
                echo "PYTHON version 2.7 or below required"
        fi
fi

if [ $HOSTNAME == "max2play" ]
then
	if [ $b -lt $a ]
	then
		echo "******************************************"
		echo "******************************************"
		echo "****                                  ****"
		echo "****              MAX2PLAY               ****"
		echo "****                                  ****"
		echo "******************************************"
		echo "******************************************"
		sudo apt-get -y update 
                sudo apt-get -y install python-rpi.gpio
		sudo apt-get -y install python-pip
		sudo apt-get -y install python-smbus 
		sudo apt-get -y install python-pil 
		#sudo apt-get -y install python-netifaces 
		sudo raspi-config nonint do_i2c 0 
		while read line
		do
			if [ "$line" == "boss2flag=1" ]
			then
				flag=1
			fi
		done < $filename
		if [ "$flag" == "1" ]
		then
			echo "already installed"
			exit 0
		else
			sudo sed -i "`wc -l < /etc/rc.local`i\\boss2flag=1\\" /etc/rc.local
			sudo sed -i "`wc -l < /etc/rc.local`i\\sudo python /opt/boss2_oled/boss2_oled.py &\\" /etc/rc.local
			echo "******************************************"
			echo "***      Successfully Installed        ***"
			echo "******************************************"
			sleep 5
			sudo reboot
		fi

	else
		#sudo apt-get -y update 
		#sudo apt-get -y install python3-pip
		#sudo apt-get -y install python3-smbus 
		#sudo apt-get -y install python3-pil 
                echo "PYTHON greater version"
                echo "PYTHON version 2.7 or below required"
	fi
fi


if [ $ropieeeflag == "1" ] || [ $ropieeeflag == "2" ]
then
                echo "******************************************"
                echo "******************************************"
                echo "****                                  ****"
                echo "****             ROPIEEE              ****"
                echo "****                                  ****"
                echo "******************************************"
                echo "******************************************"
		yes | pacman -S python2-pip gcc
#		pip2 install RPi.GPIO
		CFLAGS="-fcommon" pip2 install rpi.gpio
		pip2 install smbus
		yes | pacman -S python2-pillow
		yes | pacman -S inetutils
		while read line
                do
                        if [ "$line" == "i2c-dev" ]
                        then
                                flag=1
                        fi
                done < /etc/modules-load.d/raspberrypi.conf
                if [ "$flag" == "1" ]
                then
                        echo "already added"
			exit 0
                else
			echo "i2c-dev" >> /etc/modules-load.d/raspberrypi.conf
		fi
		cp /opt/boss2_oled/ropieee-boss2-oled.service /etc/systemd/system/
		systemctl enable ropieee-boss2-oled.service
		echo "******************************************"
                echo "***      Successfully Installed        ***"
                echo "******************************************"
                sleep 5
                reboot
fi
