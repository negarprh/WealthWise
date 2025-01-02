document.addEventListener('DOMContentLoaded', function () {
    const stockSelector = document.getElementById('stock-selector');
    const ctx = document.getElementById('stockPriceChart').getContext('2d');
    const stockPriceDisplay = document.getElementById('stock-price'); // Element to display current price
    let stockChart;

    function fetchStockData(ticker) {
        console.log(`Fetching stock data for: ${ticker}`); // Log selected ticker

        fetch(`/get-stock-data/${ticker}`)
            .then((response) => response.json())
            .then((data) => {
                console.log('API Response:', data); // Log the API response
                if (data.success) {
                    const labels = data.data.map(item => item.Date);
                    const prices = data.data.map(item => item.Close);

                    console.log('Labels:', labels); // Log chart labels
                    console.log('Prices:', prices); // Log chart data

                    updateChart(labels, prices);

                    // Update the current price display with the most recent price
                    const latestPrice = prices[prices.length - 1]; // Get the latest price
                    stockPriceDisplay.textContent = `$${latestPrice.toFixed(2)}`; // Display the price
                } else {
                    alert('Error fetching stock data: ' + data.message);
                    stockPriceDisplay.textContent = 'Unavailable'; // Clear price display on error
                }
            })
            .catch((error) => {
                console.error('Fetch error:', error);
                stockPriceDisplay.textContent = 'Error'; // Handle fetch error
            });
    }

    function updateChart(labels, prices) {
        if (stockChart) stockChart.destroy(); // Destroy previous chart
        stockChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Stock Price (USD)',
                    data: prices,
                    borderColor: 'rgba(89,181,63,0.84)',
                    borderWidth: 2,
                    fill: false,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                aspectRatio: 2,
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: 'Date',
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: 'Price (USD)',
                        }
                    }
                }
            }
        });
    }

    // Load data for the first stock on page load
    if (stockSelector.value) {
        fetchStockData(stockSelector.value);
    }

    // Update chart and price when a new stock is selected
    stockSelector.addEventListener('change', function () {
        fetchStockData(this.value);
    });
});
