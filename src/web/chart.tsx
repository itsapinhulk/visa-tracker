import MenuItem from '@mui/material/MenuItem';
import Grid from '@mui/material/Grid';
import TextField from '@mui/material/TextField';
import Button from '@mui/material/Button';
import {ChangeEvent, useMemo, useState} from "react";
import ApexChart  from "react-apexcharts";
import Box from '@mui/material/Box';
import randomColor from 'randomcolor';
import {AllCountries, AllVisaTypes, Data, MinDate, MaxDate, displayDate, MonthData} from './all_data';

interface ChartEntry {
    country: string
    category: string
}

function allMonths(startDate, endDate) {
    const months = [];
    let currentDate = startDate;
    while (currentDate <= endDate) {
        months.push(new Date(currentDate));
        // Can't believe this AI generated code works.
        currentDate = new Date(currentDate.getFullYear(), currentDate.getMonth() + 1, 1);
    }
    return months;
}

enum DateType {
    FinalActionDate, FilingDate
}

function dateTypeToString(dateType: DateType) {
    if (dateType === DateType.FinalActionDate) {
        return "Final Date";
    } else if (dateType === DateType.FilingDate) {
        return "Filing Date";
    } else {
        return "Unhandled Date Type: " + dateType;
    }
}

function createChart(chartList : ChartEntry[], minDate : Date, maxDate: Date,
                     dateType: DateType) {
    const allDates = allMonths(minDate, maxDate);

    // Add reference line
    let series = [];

    let referenceData = [];
    for (const date of allDates) {
        referenceData.push({x: date, y: date.getTime()});
    }

    series.push({
        name: "Current",
        data: referenceData,
    });

    for (const entry of chartList) {
        const countryLower = entry.country.toLowerCase();
        const categoryLower = entry.category.toLowerCase();
        const countryDisplay = AllCountries.find(c => c.toLowerCase() === countryLower);
        const categoryDisplay = AllVisaTypes.find(c => c.toLowerCase() === categoryLower);
        const currData = Data
            .filter(
                (x) => (x.country.toLowerCase() === countryLower) &&
                        (x.category.toLowerCase() === categoryLower))
            .map((entry) => ({
                x: entry.date,
                y: ((dateType === DateType.FilingDate) ? entry.filing_date?.getTime() :
                            entry.final_action_date?.getTime() ?? null),
            }))
            .filter((x) => x.y != null)
        ;
        series.push({
            name: `${countryDisplay}/${categoryDisplay}`,
            data: currData,
        });
    }

    // Reference line is grey, rest are vibrant colors.
    let allColors = ['#AAAAAA'];
    for (let i = 0; i < series.length; i++) {
        allColors.push(randomColor({seed: 2 ** (i + 10), luminosity: 'dark'}));
    }
    const options = {
        stroke: { curve: "straight" },
        markers: { size: 0},
        xaxis: {
            type: 'datetime',
        },
        tooltip: {
            x: {
                format: "yyyy MMM",
                formatter: function (value) {
                    return dateTypeToString(dateType) + " for " + displayDate(new Date(value), false)
                }
            },
            shared: false,
            fixed : {
                enabled: false,
                position: 'topLeft',
            },
            onDatasetHover : {
                highlightDataSeries: true,
            },
        },
        colors: allColors,
        yaxis: {
            labels : {
                formatter: function (value) {
                    return displayDate(new Date(value), true);
                }
            }
        },
        chart : {
            toolbar: {
                tools: {
                    download: false
                }
            },
            zoom: {
                autoScaleYaxis: true,
            }
        },
        grid: {
            position: 'front',
        },
    };

    return (
        <div className="line">
            <ApexChart options={options} series={series} type="line" width="1000px" />
        </div>
    );
}

function Chart({data}: { data: MonthData[] }) {
    const [country, setCountry] = useState<string>("");
    const [category, setCategory] = useState<string>("");

    const [dateType, setDateType] = useState<DateType>(DateType.FilingDate);
    const toggleDateType = () => {
        if (dateType === DateType.FinalActionDate) {
            setDateType(DateType.FilingDate);
        } else if (dateType === DateType.FilingDate){
            setDateType(DateType.FinalActionDate);
        } else {
            console.error("Unhandled date type: " + dateType)
        }
    }

    const handleCountryChange = (event: ChangeEvent<HTMLInputElement>) => {
        setCountry(event.target.value as string);
    };
    const handleCategoryChange = (event: ChangeEvent<HTMLInputElement>) => {
        setCategory(event.target.value as string);
    };

    const [chartList, setChartList] = useState<ChartEntry[]>([
        {country: "India", category: "EB2"},
        {country: "China", category: "EB2"},
    ]);
    const addToChart = () => {
        if (country === "" || category === "") {
            return;
        }

        setChartList((x: ChartEntry[]) => {
            let found = false;
            x.forEach((entry) => {
                if ((entry.country.toLowerCase() === country.toLowerCase()) &&
                    (entry.category.toLowerCase() === category.toLowerCase())) {
                    found = true;
                }
            });

            if (found) {
                return [...x]
            }

            return [...x, {country, category} as ChartEntry]
        });
    }

    const chartDisplay = useMemo(
        () => createChart(chartList, MinDate, MaxDate, dateType),
        [chartList, MinDate, MaxDate, dateType]
    );

    return (<div>
        <Grid container spacing={2} columns={24}
              alignItems="center"
              justifyContent="center"
        >
            <Grid size={6}>
                <TextField
                    id="country-select"
                    fullWidth
                    select
                    label="Country"
                    value={country}
                    variant="filled"
                    onChange={handleCountryChange}
                >
                    {AllCountries.map((country) => (<MenuItem key={country} value={country.toLowerCase()}>
                            {country}
                        </MenuItem>))}
                </TextField>
            </Grid>
            <Grid size={6}>
                <TextField
                    id="category-select"
                    select
                    fullWidth
                    label="Category"
                    value={category}
                    variant="filled"
                    onChange={handleCategoryChange}
                >
                    {AllVisaTypes.map((category) => (<MenuItem key={category} value={category.toLowerCase()}>
                            {category}
                        </MenuItem>))}
                </TextField>
            </Grid>
            <Grid size={4}>
                <Button onClick={addToChart}
                        variant="contained">
                    Add To Chart
                </Button>
            </Grid>
            <Grid size={4}>
                <Button onClick={() => setChartList([])}
                        variant="contained">
                    Reset Chart
                </Button>
            </Grid>
            <Grid size={4}>
                <Button onClick={toggleDateType}
                        variant="contained">
                    SHOWING {dateTypeToString(dateType)}
                </Button>
            </Grid>
        </Grid>
        <Grid size={8}>
            <Box sx={{ p: 2 }}
                 justifyContent="center"
                 alignItems="center">
                {chartDisplay}
            </Box>
        </Grid>
    </div>);
}

export default Chart;
