let currentDate = new Date();

// Allows the user to check their appointments in previous months and years
function past()
{
    let previous = document.querySelector('#pmonth');
    previous.addEventListener('click', function() {
        let month = currentDate.getMonth();
        let previousMonth = month + 1;
        let whatYear = currentDate.getFullYear();

        if (previousMonth == 1){
        previousMonth = 12;
        whatYear--;

    } else {
        previousMonth--;
    }
    // Updates the currentDate variable so user can go back and forth
    currentDate.setFullYear(whatYear);
    currentDate.setMonth(previousMonth - 1);
    // Fetches the calendar from app.py
    {fetch('/get-calendar', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
    year: whatYear,
    month: previousMonth})
    })
    .then(response => response.json())
    .then(data => {
    let new_calendar = data.new_calendar;
    // Gets the section where the current calendar is displayed
    let calendar_section = document.querySelector('#calendar');
    // Replaces the current calendar with the new one
    calendar_section.innerHTML = new_calendar;
    });}
    })}


// Allows the user to check their upcoming appointments
function future()
{
    let next = document.querySelector('#nmonth');
    next.addEventListener('click', function() {
        let month = currentDate.getMonth();
        let nextMonth = month + 1;
        let whatYear = currentDate.getFullYear();

        if (nextMonth == 12){
        nextMonth = 1;
        whatYear++;

    } else {
        nextMonth++;
    }
    // Updates the currentDate variable so user can go back and forth
    currentDate.setFullYear(whatYear);
    currentDate.setMonth(nextMonth - 1);
    // Fetches the calendar from app.py
    {fetch('/get-calendar', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
    year: whatYear,
    month: nextMonth})
    })
    .then(response => response.json())
    .then(data => {
    let new_calendar = data.new_calendar;
    // Gets the section where the current calendar is displayed
    let calendar_section = document.querySelector('#calendar');
    // Replaces the current calendar with the new one
    calendar_section.innerHTML = new_calendar;
    });}
    })}

past()
future()
