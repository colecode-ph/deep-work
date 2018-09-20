from flask import Flask, request, render_template, redirect, url_for, flash
from flask_bootstrap import Bootstrap

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
Bootstrap(app)

from sqlalchemy import create_engine, func, update, extract
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Dailyhours
from datetime import date, datetime
# add import for making custom converter class
from werkzeug.routing import BaseConverter, ValidationError

engine = create_engine('sqlite:///deepwork.db')
Base.metadata.bind = engine
# binds the engine to the Base class
# makes the connections between class definitions & corresponding tables in db
DBSession = sessionmaker(bind = engine)
# creates sessionmaker object, which establishes link of
# communication between our code executions and the engine we created
session = DBSession()
# create an instance of the DBSession  object - to make a changes
# to the database, we can call a method within the session

# Add custom converter - https://stackoverflow.com/questions/31669864/date-in-flask-url
class DateConverter(BaseConverter):
    """Extracts a ISO8601 date from the path and validates it."""
    regex = r'\d{4}-\d{2}-\d{2}'

    def to_python(self, value):
        try:
            return datetime.strptime(value, '%Y-%m-%d').date()
        except ValueError:
            raise ValidationError()

    def to_url(self, value):
        return value.strftime('%Y-%m-%d')


app.url_map.converters['date'] = DateConverter


def getMonthValues(month, year):
        """ calculate values based on integer month and year parameters """
        month_name = date(1900, month, 1).strftime('%B')
        total_month_days = (
                session.query(func.count(Dailyhours.hours_worked))
                .filter(extract('month', Dailyhours.work_date)==month)
                .filter(extract('year', Dailyhours.work_date)==year).one()
                )
        total_month_hours = (
                session.query(func.sum(Dailyhours.hours_worked))
                .filter(extract('month', Dailyhours.work_date)==month)
                .filter(extract('year', Dailyhours.work_date)==year).one()
                )
        if total_month_days[0] == 0:
            avg_hrs_day = 0 # conditional for divide by zero
        else:
            a = total_month_hours[0] / total_month_days[0]
            avg_hrs_day = format(a, '.2f')
        total_hours = session.query(func.sum(Dailyhours.hours_worked)).one()
        month_values = ([
            year,
            month_name,
            total_month_days[0],
            total_month_hours[0],
            avg_hrs_day,
            total_hours
        ])
        return month_values


@app.route('/')
def indexPage():
    """ Shows the list of workdays"""
    month = datetime.today().month
    year = datetime.today().year
    return displayMonth(month, year)


@app.route('/month/<int:month>/<int:year>/')
def displayMonth(month, year):
    month_values = getMonthValues(month, year)
    list = (
        session.query(Dailyhours).order_by(Dailyhours.work_date)
        .filter(extract('month', Dailyhours.work_date)==month)
        .filter(extract('year', Dailyhours.work_date)==year)
        )
    return render_template(
        'display_month.html',
        list = list,
        year = month_values[0],
        month_name = month_values[1],
        days_worked_month = month_values[2],
        hours_worked_month = month_values[3],
        avg_hrs_day = month_values[4],
        total_hours = month_values[5]
        )

@app.route('/totals')
def monthly_totals():
    month = datetime.today().month
    year = datetime.today().year

    monthly_totals = []

    earliest_year = session.query(func.min(Dailyhours.work_date)).one()
    print(earliest_year[0].year)
    earliest_year = earliest_year[0].year

    while year >= earliest_year:

        while month > 0:
            month_values = getMonthValues(month, year)
            monthly_totals.append(month_values)
            month = month - 1

        year = year -1
        month = 12

    return render_template(
        'monthly_totals.html',
        totals = monthly_totals,
        )


@app.route('/add/', methods=['GET', 'POST'])
def addDay():
    """ Form to add a new work day entry, and logic to POST it to db """
    if request.method == 'POST':
        new_date = Dailyhours(
            work_date = datetime.strptime(
                request.form['work_date'], "%Y-%m-%d"),
            hours_worked = (request.form['hours_worked']),
            remarks = (request.form['remarks'])
            )
        session.add(new_date)
        session.commit()
        return redirect(url_for('indexPage'))
    else:
        return render_template('add_day.html')


@app.route('/delete/<date:work_date>/', methods=['GET', 'POST'])
def deleteDay(work_date):
    """ Page to delete a day row entry from the database """
    day_to_delete = session.query(Dailyhours).filter_by(work_date = work_date).one()

    if request.method == 'POST':
        session.delete(day_to_delete)
        session.commit()
        # flash message here
        return redirect(url_for('indexPage'))
    else:
         return render_template('delete_day.html', day_to_delete = day_to_delete)


@app.route('/edit/<date:work_date>/', methods=['GET', 'POST'])
def editDay(work_date):
    """ Page to edit a day row entry from the database """
    day_to_edit = session.query(Dailyhours).filter_by(work_date = work_date).one()

    if request.method == 'POST':
        data = ({'hours_worked': request.form['hours_worked'],
                'remarks': request.form['remarks']}
                )
        session.query(Dailyhours).filter_by(work_date = work_date).update(data)
        session.commit()
        return redirect(url_for('indexPage'))
    else:
         return render_template('edit_day.html', day_to_edit = day_to_edit)


if __name__ == '__main__':
    app.debug = True
    app.run(host = '0.0.0.0', port = 5001)