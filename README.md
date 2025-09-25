# On-road Vehicle Breakdown Assistance Finder

This is a Django-based web application to help users find vehicle breakdown assistance services nearby.

## Features
- User registration and login
- Mechanic registration
- Service request management
- Profile management with profile picture upload
- Payment integration (Stripe)

## Setup Instructions
1. Clone the repository:
   ```sh
   git clone https://github.com/Hruthikgowdahk/On-road-vehicle-breakdown-assistance-finder.git
   ```
2. Navigate to the project directory:
   ```sh
   cd "on road vehicle breakdown/on road vehicle breakdown"
   ```
3. Install dependencies:
   ```sh
   pip install -r requirements.txt
   ```
4. Run migrations:
   ```sh
   python index.py migrate
   ```
5. Create a superuser (optional):
   ```sh
   python index.py createsuperuser
   ```
6. Start the development server:
   ```sh
   python index.py runserver
   ```

## Usage
- Access the app at [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- Register as a user or mechanic
- Request or provide breakdown assistance

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details. 