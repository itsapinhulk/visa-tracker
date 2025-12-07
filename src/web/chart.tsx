import MenuItem from '@mui/material/MenuItem';
import Grid from '@mui/material/Grid';
import TextField from '@mui/material/TextField';
import FormGroup from '@mui/material/FormGroup';
import Checkbox from '@mui/material/Checkbox';
import Button from '@mui/material/Button';
import Radio from '@mui/material/Radio';
import RadioGroup from '@mui/material/RadioGroup';
import FormControlLabel from '@mui/material/FormControlLabel';
import FormLabel from '@mui/material/FormLabel';
import {ChangeEvent, useMemo, useState} from "react";
import ApexChart  from "react-apexcharts";
import Box from '@mui/material/Box';
import randomColor from 'randomcolor';
import {AllCountries, AllVisaTypes, Data, MinDate, MaxDate, displayDate, MonthData} from './all_data';

interface ChartEntry {
    country: string
    category: string
}

function calculateRegression(data: { x: Date; y: number }[]): { slope: number; intercept: number } {
    const n = data.length;
    const xVals = data.map(d => d.x.getTime());
    const yVals = data.map(d => d.y);

    const sumX = xVals.reduce((a, b) => a + b, 0);
    const sumY = yVals.reduce((a, b) => a + b, 0);
    const sumXY = xVals.reduce((sum, x, i) => sum + x * yVals[i], 0);
    const sumXX = xVals.reduce((sum, x) => sum + x * x, 0);

    const slope = (n * sumXY - sumX * sumY) / (n * sumXX - sumX * sumX);
    const intercept = (sumY - slope * sumX) / n;

    return {slope, intercept};
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
                     dateType: DateType, showEstimate: boolean, estimatePeriod : number) {
    const allDates = allMonths(minDate, maxDate);

    // Add reference line
    let series = [];

    let referenceData = [];
    let referenceEndDate = maxDate;
    if (showEstimate) {
        referenceEndDate = new Date(maxDate.getFullYear() + 5, maxDate.getMonth(), 1);
    }
    const referenceDates = allMonths(minDate, referenceEndDate);
    for (const date of referenceDates) {
        referenceData.push({x: date, y: date.getTime()});
    }

    series.push({
        name: "Current",
        data: referenceData,
    });

    // Reference line is grey, rest are vibrant colors.
    let allColors = ['#AAAAAA'];
    let targetColors = [];
    for (let i = 0; i < chartList.length; i++) {
        targetColors.push(randomColor({seed: 2 ** (i + 10), luminosity: 'dark'}));
    }

    chartList.forEach((entry, index) => {
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
        allColors.push(targetColors[index]);

        if (showEstimate && currData.length > 0) {
            const estimateMonths = estimatePeriod * 12;
            const recentData = currData.slice(-estimateMonths);

            if (recentData.length >= 2) {
                const regression = calculateRegression(recentData);
                const lastDate = new Date(currData[currData.length - 1].x);
                const futureMonths = allMonths(
                    new Date(lastDate.getFullYear(), lastDate.getMonth() + 1, 1),
                    new Date(lastDate.getFullYear() + 5, lastDate.getMonth(), 1)
                );

                const lastDataPoint = currData[currData.length - 1];
                const predictions = futureMonths.map(date => ({
                    x: date,
                    y: lastDataPoint.y + regression.slope * (date.getTime() - lastDataPoint.x.getTime())
                }));

                series.push({
                    name: `${countryDisplay}/${categoryDisplay} (Estimate)`,
                    data: [lastDataPoint, ...predictions],
                    dashArray: [5, 5]
                });

                const lighterColor = randomColor({
                    seed: 2 ** (index + 10),
                    luminosity: 'light',
                    hue: targetColors[index]
                });
                allColors.push(lighterColor);
            }
        }
    });

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
            <ApexChart options={options} series={series} type="line" width="900px" />
        </div>
    );
}

function Chart({data}: { data: MonthData[] }) {
    const [country, setCountry] = useState<string>("");
    const [category, setCategory] = useState<string>("");

    const [dateType, setDateType] = useState<DateType>(DateType.FilingDate);

    const [showEstimate, setShowEstimate] = useState<boolean>(false);
    const [estimatePeriod, setEstimatePeriod] = useState<number>(1);

    const handleDateTypeChange = (event: ChangeEvent<HTMLInputElement>) => {
        setDateType(parseInt(event.target.value) as DateType);
    };

    const handleEstimateChange = (event: ChangeEvent<HTMLInputElement>) => {
        setShowEstimate(event.target.checked);
    };

    const handleEstimatePeriodChange = (event: ChangeEvent<HTMLInputElement>) => {
        setEstimatePeriod(parseInt(event.target.value));
    };

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
        () => createChart(chartList, MinDate, MaxDate, dateType,
                            showEstimate, estimatePeriod),
        [chartList, MinDate, MaxDate, dateType, showEstimate, estimatePeriod]
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
                        variant="contained"
                        color="error">
                    Reset Chart
                </Button>
            </Grid>
        </Grid>
        <Grid container spacing={2} columns={24}
              alignItems="center"
              justifyContent="center"
              sx={{mt: 2}}
        >
            <Grid size={12}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                    <FormLabel>Date Type: </FormLabel>
                    <RadioGroup
                        value={dateType}
                        onChange={handleDateTypeChange}
                        row
                        sx={{ flexWrap: 'nowrap' }}
                    >
                        <FormControlLabel
                            value={DateType.FilingDate}
                            control={<Radio />}
                            label="Filing Date"
                        />
                        <FormControlLabel
                            value={DateType.FinalActionDate}
                            control={<Radio />}
                            label="Final Action Date"
                        />
                    </RadioGroup>
                </Box>
            </Grid>
            <Grid size={8}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                    <FormGroup row>
                        <FormControlLabel
                            control={
                                <Checkbox
                                    checked={showEstimate}
                                    onChange={handleEstimateChange}
                                />
                            }
                            label="Estimate using"
                        />
                        <TextField
                            select
                            disabled={!showEstimate}
                            value={estimatePeriod}
                            onChange={handleEstimatePeriodChange}
                            variant="standard"
                            sx={{minWidth: 120}}
                        >
                            <MenuItem value={1}>1 year</MenuItem>
                            <MenuItem value={2}>2 years</MenuItem>
                            <MenuItem value={5}>5 years</MenuItem>
                        </TextField>
                    </FormGroup>
                </Box>
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
