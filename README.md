# Business Intelligence Web Application

This project is a Business Intelligence web application built with Next.js for the frontend and Flask for the backend API.

## Prerequisites

- Node.js (v14 or later)
- Python (v3.7 or later)
- pip (Python package installer)

## Setup

### Frontend (Next.js)

1. Navigate to the `bi_web` directory:
   ```
   cd bi_web
   ```

2. Install dependencies:
   ```
   npm install
   ```

3. Create a `.env.local` file in the `bi_web` directory and add the following:
   ```
   NEXT_PUBLIC_API_BASE_URL=http://localhost:5000/api
   ```

4. Start the development server:
   ```
   npm run dev
   ```

The frontend will be available at `http://localhost:3000`.

### Backend (Flask)

1. Navigate to the `bi_api` directory:
   ```
   cd bi_api
   ```

2. Create a virtual environment:
   ```
   python -m venv venv
   ```

3. Activate the virtual environment:
   - On Windows:
     ```
     venv\Scripts\activate
     ```
   
4. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

5. Set up the database and run migrations:
   ```
   flask db upgrade
   ```

7. To expose your local server to the internet using ngrok:
   
   a. Install ngrok from https://ngrok.com/download
   
   b. Run ngrok:
      ```
      ngrok http 5000
      ```
   
   c. Copy the HTTPS URL provided by ngrok (e.g., https://12345678.ngrok.io)
   
   d. Update the `NEXT_PUBLIC_API_BASE_URL` in your frontend `.env.local` file:
      ```
      NEXT_PUBLIC_API_BASE_URL=https://12345678.ngrok.io/api
      ```
   
   Note: Remember to update this URL whenever you restart ngrok, as it generates a new URL each time.

6. Run the Flask application:
   ```
   python run.py
   ```

The API will be available at `http://localhost:5000`.

## Usage

After setting up both the frontend and backend, you can use the application by navigating to `http://localhost:3000` in your web browser.

## Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details.


Chatbot Training Data

# Sample Questions for ChatbotService

Here's a list of questions that the ChatbotService is designed to handle, organized by topic:

1. Sales Insights:
   - What are our monthly sales trends?
   - Can you show me the sales over time?
   - Which are the top-selling products?

2. Customer Insights:
   - How are our customer segments distributed?
   - What's the frequency of customer purchases?

3. Product and Price Analysis:
   - Can you explain the relationship between quantity and price?
   - How are the performance of different product categories?   

4. Orders Overview:
   - What's the current order status distribution? "# Business-Intelligence-App" 
"# Business-Intelligence-App" 
