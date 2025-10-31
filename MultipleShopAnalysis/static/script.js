fetch('/api/sales-summary')
  .then(res => res.json())
  .then(data => {
    document.getElementById('total-sales').textContent = data.total_sales;
    document.getElementById('best-item').textContent = data.best_selling;
    document.getElementById('trend-icon').textContent = data.trend === 'up' ? '🔼' : '🔽';

    // Dummy sparkline data
    const ctx = document.getElementById('sparkline').getContext('2d');
    new Chart(ctx, {
      type: 'line',
      data: {
        labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
        datasets: [{
          data: [1200, 1500, 1000, 1700, 1300, 1800, data.revenue],
          borderColor: '#007bff',
          fill: false,
          tension: 0.3
        }]
      },
      options: {
        plugins: { legend: { display: false } },
        scales: { x: { display: false }, y: { display: false } }
      }
    });
  });
