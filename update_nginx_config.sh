apt install nginx -y
cp nginx_config.txt /etc/nginx/sites-available/netrefer_api_interface
ln -s /etc/nginx/sites-available/netrefer_api_interface /etc/nginx/sites-enabled/
nginx -t
service nginx restart