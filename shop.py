import streamlit as st
import json
import os
import pandas as pd
import folium
from streamlit_folium import st_folium
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
from geopy.distance import geodesic
import webbrowser
from prettytable import PrettyTable

SHOP_LOCATION = {'latitude': 13.057088744468263, 'longitude': 80.19379382359077}  # Shop's latitude and longitude


class HashTable:
    def _init_(self, size=10):
        self.size = size

        self.table = [[] for _ in range(size)]

    def hash_function(self, key):
        return hash(key) % self.size

    def insert(self, key, value):
        index = self.hash_function(key)
        self.table[index].append((key, value))

    def search(self, key):
        index = self.hash_function(key)
        for pair in self.table[index]:
            if pair[0] == key:
                return pair[1]
        return None


class Queue:
    def _init_(self):
        self.items = []

    def is_empty(self):
        return len(self.items) == 0

    def enqueue(self, item):
        self.items.append(item)

    def dequeue(self):
        if not self.is_empty():
            return self.items.pop(0)
        return None

    def size(self):
        return len(self.items)

    def peek(self):
        if not self.is_empty():
            return self.items[0]
        return None

    def to_list(self):
        return self.items.copy()


def read_inventory():
    inventory_hash_table = HashTable()
    with open('inventory.json', 'r') as file:
        inventory_data = json.load(file)
        for item, details in inventory_data.items():
            inventory_hash_table.insert(item, details)
    return inventory_hash_table


def read_bills():
    bills_queue = Queue()
    if os.path.exists('bills.json'):
        with open('bills.json', 'r') as file:
            try:
                bills = json.load(file)
                for bill in bills:
                    bills_queue.enqueue(bill)
            except json.JSONDecodeError:
                pass
    return bills_queue


def write_bills(bills_queue):
    with open('bills.json', 'w') as file:
        json.dump(bills_queue.to_list(), file, indent=4)


def display_bill_table(bill, inventory_hash_table):
    cart = bill['cart']
    table = PrettyTable(["Vegetable", "Quantity", "Price", "Amount"])
    total = 0
    for item in cart:
        veg_name = item['vegetable']
        quantity = item['quantity']
        item_details = inventory_hash_table.search(veg_name)
        if item_details:
            price_per_unit = item_details['price']
            amount = quantity * price_per_unit
            total += amount
            table.add_row([veg_name, quantity, f"₹{price_per_unit:.2f}", f"₹{amount:.2f}"])
        else:
            table.add_row([veg_name, quantity, "Not found", "N/A"])
    table.add_row(["Total", "", "", f"₹{total:.2f}"])
    print(table)


def welcome_page():
    set_page_style(bg_color="#ccffcc", text_color="#ffff00", header_color="#ff7f00", button_color="#800080")
    set_background_image("https://i.pinimg.com/736x/04/e5/47/04e5479ee632f638057d6521582f2cd7.jpg")
    st.title("WELCOME TO RAM STORES")
    st.text("Select your role")
    if st.button("Vendor"):
        st.session_state.page = "vendor_login"
    elif st.button("Customer"):
        st.session_state.page = "customer_login"


def customer_login():
    st.subheader("Customer Login")
    customer_username = st.text_input("Username")
    customer_password = st.text_input("Password", type="password")
    if st.button("Login"):
        if customer_exists(customer_username):
            if get_customer_password(customer_username) == customer_password:
                st.session_state.logged_in = True
                st.session_state.user_type = "Customer"
                st.session_state.username = customer_username
                st.success("Customer logged in successfully!")
                st.session_state.page = "customer_dashboard"
            else:
                st.error("Incorrect password!")
        else:
            st.warning("User does not exist. Please sign up.")
    if st.button("Sign Up"):
        st.session_state.page = "customer_signup"


def customer_signup():
    st.subheader("Customer Sign Up")
    customer_username = st.text_input("Gmail")
    customer_password = st.text_input("Password", type="password")
    if st.button("Sign Up"):
        if not customer_exists(customer_username):
            write_customer_data(customer_username, customer_password)
            st.success("User registered successfully! Please login.")
            st.session_state.page = "customer_login"
            send_email(customer_username, "Welcome to Online Door Delivery Vegetable Shopping",
                       "Thank you for signing up!")
        else:
            st.error("User already exists!")


def send_email(to_email, subject, body):
    from_email = "onlinevegetablemarketting740@gmail.com"
    from_password = "yyor wfcc skiz kgwz"
    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(from_email, from_password)
        server.sendmail(from_email, to_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"Failed to send email. Error: {e}")
        return False


def customer_exists(username):
    if os.path.exists('customers.json'):
        with open('customers.json', 'r') as file:
            try:
                customers = json.load(file)
                return username in customers
            except json.JSONDecodeError:
                return False
    return False


def write_customer_data(username, password):
    customers = {}
    if os.path.exists('customers.json'):
        with open('customers.json', 'r') as file:
            try:
                customers = json.load(file)
            except json.JSONDecodeError:
                customers = {}
    customers[username] = password
    with open('customers.json', 'w') as file:
        json.dump(customers, file)


def get_customer_password(username):
    if os.path.exists('customers.json'):
        with open('customers.json', 'r') as file:
            try:
                customers = json.load(file)
                return customers.get(username)
            except json.JSONDecodeError:
                return None
    return None


def get_inventory():
    if os.path.exists('inventory.json'):
        with open('inventory.json', 'r') as file:
            try:
                return json.load(file)
            except json.JSONDecodeError:
                return {}
    return {}


def update_inventory(vegetable, quantity, price=None):
    inventory = get_inventory()
    if quantity == 0:
        if vegetable in inventory:
            del inventory[vegetable]
    else:
        if vegetable in inventory:
            inventory[vegetable]['quantity'] = quantity
            inventory[vegetable]['price'] = price
        else:
            inventory[vegetable] = {'quantity': quantity, 'price': price}
    with open('inventory.json', 'w') as file:
        json.dump(inventory, file)


def get_google_maps_url(shop_location, customer_location):
    shop_coords = f"{shop_location['latitude']},{shop_location['longitude']}"
    customer_coords = f"{customer_location['latitude']},{customer_location['longitude']}"
    return f"https://www.google.com/maps/dir/{shop_coords}/{customer_coords}"


def get_route_and_time(shop_location, customer_location):
    try:
        response = requests.get(
            f"http://router.project-osrm.org/route/v1/driving/{shop_location['longitude']},{shop_location['latitude']};{customer_location['longitude']},{customer_location['latitude']}?overview=false"
        )
        data = response.json()
        route = data['routes'][0]['geometry']
        estimated_time = data['routes'][0]['duration'] / 60  # Convert seconds to minutes
        return route, estimated_time
    except Exception as e:
        print(f"Error calculating route: {e}")
        return None, None


def get_order_history(username):
    bills_queue = read_bills()
    order_history = [bill for bill in bills_queue.to_list() if bill['customer'] == username]
    return order_history


def set_page_style(bg_color, text_color, header_color, button_color):
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-color: {bg_color};
        }}
        .stApp * {{
            color: {text_color} !important;
        }}
        .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6 {{
            color: {header_color} !important;
        }}
        .stButton>button {{
            background-color: {button_color};
            color: {text_color};
        }}
        </style>
        """,
        unsafe_allow_html=True
    )


def set_background_image(image_url):
    # Inject custom CSS for background image
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-image: url("{image_url}");
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )


def customer_dashboard():
    st.subheader("Customer Dashboard")
    st.subheader("Shop Vegetables")
    inventory = get_inventory()
    if 'cart' not in st.session_state:
        st.session_state.cart = Queue()

    cart_list = st.session_state.cart.to_list()

    for veg, details in inventory.items():
        st.text(f"{veg}: {details['quantity']} units at ₹{details['price']:.2f} each")
        quantity = st.number_input(f"Quantity of {veg}", min_value=0, max_value=details['quantity'], key=veg)
        if quantity > 0:
            found = False
            for item in cart_list:
                if item['vegetable'] == veg:
                    item['quantity'] = quantity
                    found = True
                    break
            if not found:
                st.session_state.cart.enqueue({'vegetable': veg, 'quantity': quantity, 'price': details['price']})
            else:
                # Update the queue with the modified cart_list
                st.session_state.cart = Queue()
                for item in cart_list:
                    st.session_state.cart.enqueue(item)

    st.subheader("Set Delivery Location")
    default_location = [20.5937, 78.9629]  # Default location set to the center of India
    m = folium.Map(location=default_location, zoom_start=5)
    marker = folium.Marker(location=default_location, draggable=True)
    marker.add_to(m)
    map_output = st_folium(m, width=700, height=500)
    if map_output and 'last_object_clicked' in map_output and map_output['last_object_clicked'] is not None:
        location = map_output['last_object_clicked']
        st.session_state.location = {'latitude': location['lat'], 'longitude': location['lng']}
        st.text(f"Location set to: {st.session_state.location}")

    if st.button("Generate Bill"):
        if not st.session_state.cart.is_empty():
            total_amount = sum(item['quantity'] * item['price'] for item in st.session_state.cart.to_list())
            if total_amount >= 100:
                st.session_state.page = 'checkout'
            else:
                st.warning("The total order amount must be at least ₹100.")

    st.subheader("Order History")
    order_history = get_order_history(st.session_state.username)
    if order_history:
        for index, bill in enumerate(order_history):
            st.text(f"Order #{index + 1}")
            total = bill.get('total', 0.0)  # Get total or default to 0.0 if not present
            st.text(f"Total: ₹{total:.2f}")
            st.text(f"Status: {bill.get('status', 'Pending')}")
            location = bill.get('location')
            if location:
                st.text(f"Location: {location}")
                latitude, longitude = location['latitude'], location['longitude']
                m = folium.Map(location=[latitude, longitude], zoom_start=15)
                folium.Marker([latitude, longitude], popup="Delivery Location").add_to(m)
                st_folium(m, key=f"history_map_{index}")
                if bill.get('route'):
                    folium.PolyLine(bill['route'], color="blue", weight=2.5, opacity=1).add_to(m)
                    st_folium(m, key=f"route_map_{index}")
                google_maps_url = get_google_maps_url(SHOP_LOCATION, location)
                if st.button("Open Route in Google Maps", key=f"google_maps_{index}"):
                    webbrowser.open_new_tab(google_maps_url)
            st.text(f"Estimated Delivery Time: {bill.get('estimated_time', 'N/A')} minutes")
            st.text("\n")
    else:
        st.text("No orders yet.")


def vendor_login():
    # set_page_style(bg_color="#ccffcc", text_color="#000000", header_color="#008000", button_color="#98fb98")
    st.subheader("Vendor Login")
    vendor_username = st.text_input("Username")
    vendor_password = st.text_input("Password", type="password")
    if st.button("Login"):
        if vendor_username == "onlinevegetablemarketting740@gmail.com" and vendor_password == "vegetable":
            st.session_state.logged_in = True
            st.session_state.user_type = "Vendor"
            st.session_state.username = vendor_username
            st.success("Vendor logged in successfully!")
            st.session_state.page = "vendor_dashboard"
        else:
            st.error("Invalid vendor credentials!")


def vendor_dashboard():
    st.subheader("Vendor Dashboard")
    # Display inventory
    st.subheader("Current Inventory")
    inventory = get_inventory()
    if inventory:
        for veg, details in inventory.items():
            st.text(f"{veg}: {details['quantity']} units at ₹{details['price']:.2f} each")
    else:
        st.text("No inventory available.")
        # Add new inventory items
    st.subheader("Add New Inventory Item")
    new_veg = st.text_input("Vegetable Name")
    new_quantity = st.number_input("Quantity", min_value=0)
    new_price = st.number_input("Price per unit", min_value=0.0, format="%.2f")
    if st.button("Add/Update Inventory"):
        update_inventory(new_veg, new_quantity, new_price)
        st.success(f"{new_veg} inventory updated successfully!")
    # Display orders
    st.subheader("Orders")
    orders = []
    if os.path.exists('bills.json'):
        with open('bills.json', 'r') as file:
            try:
                orders = json.load(file)
            except json.JSONDecodeError:
                orders = []
    if orders:
        for index, order in enumerate(orders):
            st.text(f"Order #{index + 1}")
            st.text(f"Customer: {order['customer']}")
            total = order.get('total', 0)  # Use get to provide a default value if 'total' is missing
            st.text(f"Total: ₹{total:.2f}")
            st.text(f"Status: {order.get('status', 'Pending')}")
            location = order.get('location')
            if location:
                st.text(f"Delivery Location: {location}")
                latitude, longitude = location['latitude'], location['longitude']
                m = folium.Map(location=[latitude, longitude], zoom_start=15)
                folium.Marker([latitude, longitude], popup="Delivery Location").add_to(m)
                st_folium(m, key=f"order_map_{index}")
                # Add route as a polyline on the map
                if order.get('route'):
                    folium.PolyLine(order['route'], color="blue", weight=2.5, opacity=1).add_to(m)
                    st_folium(m, key=f"route_map_{index}")
                google_maps_url = get_google_maps_url(SHOP_LOCATION, location)
                if st.button("Open Route in Google Maps", key=f"google_maps_{index}"):
                    webbrowser.open_new_tab(google_maps_url)
            st.text(f"Estimated Delivery Time: {order.get('estimated_time', 'N/A')} minutes")
            st.text("\n")
    else:
        st.text("No orders yet.")


def generate_bill(customer_username, cart, location):
    def display_bill_using_hash_table(cart):
        inventory_hash_table = read_inventory()
        total_amount = 0
        bill_items = []
        for item in cart:
            veg_name = item['vegetable']
            quantity = item['quantity']
            item_details = inventory_hash_table.search(veg_name)
            if item_details:
                price_per_unit = item_details['price']
                amount = quantity * price_per_unit
                total_amount += amount
                bill_items.append({'vegetable': veg_name, 'quantity': quantity, 'price': price_per_unit})
        bill = {
            'customer': customer_username,
            'cart': bill_items,
            'total': total_amount,
            'location': location
        }
        bills_queue = read_bills()
        bills_queue.enqueue(bill)
        write_bills(bills_queue)
        return bill

    return display_bill_using_hash_table(cart)


def checkout(cart=None):
    if cart is None and 'cart' not in st.session_state:
        st.session_state.cart = Queue()  # Initialize Queue if not already in session state

    st.subheader("Checkout")

    # Check if cart is not empty and location is set
    if not st.session_state.cart.is_empty() and 'location' in st.session_state:
        cart_list = st.session_state.cart.to_list()  # Convert Queue to list

        location = st.session_state.location

        # Generate bill based on username, cart_list (converted to list), and location
        bill = generate_bill(st.session_state.username, cart_list, location)

        if bill:
            st.success("Bill generated successfully!")
            # Create bill table
            bill_data = {'Vegetable': [], 'Quantity': [], 'Price per unit': [], 'Amount': []}

            for item in cart_list:
                bill_data['Vegetable'].append(item['vegetable'])
                bill_data['Quantity'].append(item['quantity'])
                bill_data['Price per unit'].append(f"₹{item['price']:.2f}")
                bill_data['Amount'].append(f"₹{item['quantity'] * item['price']:.2f}")

            bill_table = pd.DataFrame(bill_data)
            st.table(bill_table)

            # Display total amount
            st.text(f"Total: ₹{bill['total']:.2f}")

            # Display delivery location on map
            latitude, longitude = location['latitude'], location['longitude']
            m = folium.Map(location=[latitude, longitude], zoom_start=15)
            folium.Marker([latitude, longitude], popup="Delivery Location").add_to(m)
            st_folium(m)

            # Send bill email to customer
            bill_body = f"Hello {st.session_state.username},\n\nHere is your bill:\n\n"
            bill_body += bill_table.to_string(index=False) + "\n\n"
            bill_body += f"Total: ₹{bill['total']:.2f}\n\nThank you for shopping with us!"

            send_email(st.session_state.username, "Your Bill from Online Door Delivery Vegetable Shopping", bill_body)

            # Display Google Maps link
            google_maps_url = get_google_maps_url(SHOP_LOCATION, location)
            if st.button("Open Route in Google Maps"):
                webbrowser.open_new_tab(google_maps_url)

        else:
            st.warning("Failed to generate bill. Please try again later.")

    else:
        st.warning("Your cart is empty or location not set.")


def confirm_order():
    st.subheader("Confirm Order")
    customer_location = {'latitude': st.number_input("Latitude"), 'longitude': st.number_input("Longitude")}

    if st.button("Place Order"):
        order = {
            'bill_id': f"bill_{read_bills().size() + 1}",
            'customer_username': st.session_state.username,
            'cart': st.session_state.cart,
            'date': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S'),
            'customer_location': customer_location
        }

        # Update inventory quantities
        inventory = get_inventory()
        for item in st.session_state.cart:
            veg_name = item['vegetable']
            quantity_ordered = item['quantity']
            if veg_name in inventory:
                inventory[veg_name]['quantity'] -= quantity_ordered
                if inventory[veg_name]['quantity'] < 0:
                    inventory[veg_name]['quantity'] = 0

        # Save updated inventory back to inventory.json
        with open('inventory.json', 'w') as file:
            json.dump(inventory, file, indent=4)

        # Update bills.json with the new order
        bills_queue = read_bills()
        bills_queue.enqueue(order)
        write_bills(bills_queue)

        st.session_state.page = "order_placed"

    if st.button("Back"):
        st.session_state.page = "checkout"


# Run the app
if 'page' not in st.session_state:
    st.session_state.page = "welcome"

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if st.session_state.page == "welcome":
    welcome_page()
elif st.session_state.page == "customer_login":
    customer_login()
elif st.session_state.page == "customer_signup":
    customer_signup()
elif st.session_state.page == "customer_dashboard":
    customer_dashboard()
elif st.session_state.page == "checkout":
    checkout()
elif st.session_state.page == "confirm_order":
    confirm_order()
elif st.session_state.page == "order_placed":
    order_placed()
elif st.session_state.page == "vendor_login":
    vendor_login()
elif st.session_state.page == "vendor_dashboard":
    vendor_dashboard()