import MenuItem from '@mui/material/MenuItem';
import Grid from '@mui/material/Grid';
import TextField from '@mui/material/TextField';
import FormGroup from '@mui/material/FormGroup';
import Checkbox from '@mui/material/Checkbox';
import Button from '@mui/material/Button';
import Chip from '@mui/material/Chip';
import Radio from '@mui/material/Radio';
import RadioGroup from '@mui/material/RadioGroup';
import FormControlLabel from '@mui/material/FormControlLabel';
import FormLabel from '@mui/material/FormLabel';
import {ChangeEvent, useCallback, useEffect, useMemo, useRef, useState} from "react";
import ApexChart from "react-apexcharts";
import Box from '@mui/material/Box';
import randomColor from 'randomcolor';
import {AllCountries, AllVisaTypes, Data, displayDate, MaxDate, MinDate, MonthData} from './all_data';

interface ChartEntry {
    country: string
    category: string
}

interface ZoomRange {
    min: number
    max: number
}

function calculateSlope(data: { x: Date; y: number }[]): { slope: number; intercept: number } {
    const first = data[0];
    const last = data[data.length - 1];
    return (last.y - first.y) / (last.x.getTime() - first.x.getTime());
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

const numberOfEstimateYears = 10;

interface EntryData {
    currData: { x: Date; y: number }[]
    estimate: {
        slope: number
        lastDataPoint: { x: Date; y: number }
        lastDate: Date
        predictions: { x: Date; y: number }[]
    } | null
}

// Build the actual (and optional estimate) data for a single chart entry under a
// given date type. Extracted so the y-axis range can be computed across both
// date types, keeping the axis stable when the user toggles between them.
function buildEntryData(entry: ChartEntry, dateType: DateType,
                        showEstimate: boolean, estimatePeriod: number): EntryData {
    const countryLower = entry.country.toLowerCase();
    const categoryLower = entry.category.toLowerCase();
    const currData = Data
        .filter(
            (x) => (x.country.toLowerCase() === countryLower) &&
                    (x.category.toLowerCase() === categoryLower))
        .map((e) => ({
            x: e.date,
            y: ((dateType === DateType.FilingDate) ? e.filing_date?.getTime() :
                        e.final_action_date?.getTime() ?? null),
        }))
        .filter((x) => x.y != null)
    ;

    let estimate: EntryData["estimate"] = null;
    if (showEstimate && currData.length > 0) {
        const estimateMonths = estimatePeriod * 12;
        const recentData = currData.slice(-estimateMonths);

        if (recentData.length >= 2) {
            const slope = calculateSlope(recentData);
            const lastDataPoint = currData[currData.length - 1];
            const lastDate = new Date(lastDataPoint.x);
            const futureMonths = allMonths(
                new Date(lastDate.getFullYear(), lastDate.getMonth() + 1, 1),
                new Date(lastDate.getFullYear() + numberOfEstimateYears, lastDate.getMonth(), 1)
            );

            const predictions = futureMonths.map(date => ({
                x: date,
                y: lastDataPoint.y + slope * (date.getTime() - lastDataPoint.x.getTime())
            }));

            estimate = {slope, lastDataPoint, lastDate, predictions};
        }
    }

    return {currData, estimate};
}

const STORAGE_KEY = "visa-tracker-chart-state";

interface PersistedState {
    chartList: ChartEntry[]
    dateType: DateType
    showEstimate: boolean
    estimatePeriod: number
    targetDateStr: string
}

const defaultState: PersistedState = {
    chartList: [
        {country: "India", category: "EB2"},
        {country: "China", category: "EB2"},
    ],
    dateType: DateType.FilingDate,
    showEstimate: true,
    estimatePeriod: 2,
    targetDateStr: "",
};

function loadState(): PersistedState {
    if (typeof window === "undefined") return defaultState;
    try {
        const raw = window.localStorage.getItem(STORAGE_KEY);
        if (!raw) return defaultState;
        const parsed = JSON.parse(raw);
        // Only carry over known keys; drop anything extraneous in stored JSON.
        const result = {...defaultState};
        for (const key of Object.keys(defaultState) as (keyof PersistedState)[]) {
            if (parsed[key] !== undefined) {
                (result as any)[key] = parsed[key];
            }
        }
        // Fall back to the default charts if none were persisted.
        if (!Array.isArray(result.chartList) || result.chartList.length === 0) {
            result.chartList = defaultState.chartList;
        }
        return result;
    } catch (e) {
        console.warn("Failed to load persisted chart state:", e);
        return defaultState;
    }
}

function createChartData(chartList : ChartEntry[], minDate : Date, maxDate: Date,
                     dateType: DateType, showEstimate: boolean, estimatePeriod : number,
                     targetDate: Date | null,
                     zoomRange: ZoomRange | null,
                     onZoomChange: (range: ZoomRange | null) => void) {
    // Add reference line
    let series = [];

    let referenceData = [];
    let referenceEndDate = maxDate;
    if (showEstimate) {
        referenceEndDate = new Date(
            maxDate.getFullYear() + numberOfEstimateYears,
            maxDate.getMonth(), 1
        );
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
    let targetDashArray = [0];
    let crossingAnnotations = [];

    chartList.forEach((entry, index) => {
        const countryLower = entry.country.toLowerCase();
        const categoryLower = entry.category.toLowerCase();
        const countryDisplay = AllCountries.find(c => c.toLowerCase() === countryLower);
        const categoryDisplay = AllVisaTypes.find(c => c.toLowerCase() === categoryLower);
        const {currData, estimate} = buildEntryData(entry, dateType, showEstimate, estimatePeriod);

        series.push({
            name: `${countryDisplay}/${categoryDisplay}`,
            data: currData,
        });
        allColors.push(targetColors[index]);
        targetDashArray.push(0);

        const targetT = targetDate?.getTime() ?? null;

        // Annotate where actual data first crosses the target date line (y >= targetT)
        const actualCrossing = targetT != null ? currData.find(pt => pt.y >= targetT) : null;
        if (actualCrossing && targetT != null) {
            crossingAnnotations.push({
                x: actualCrossing.x.getTime(),
                y: targetT,
                marker: { size: 4, fillColor: targetColors[index], strokeColor: targetColors[index] },
                label: {
                    text: `${countryDisplay}/${categoryDisplay}`,
                    textAnchor: 'start',
                    offsetX: 4,
                    offsetY: -4,
                    style: { color: targetColors[index], background: 'white', border: 0, fontSize: '11px' },
                },
            });
        }

        if (estimate) {
            const {slope, lastDataPoint, lastDate, predictions} = estimate;
            series.push({
                name: `${countryDisplay}/${categoryDisplay} (Estimate)`,
                data: [lastDataPoint, ...predictions],
            });

            const lighterColor = randomColor({
                seed: 2 ** (index + 10),
                luminosity: 'light',
                hue: targetColors[index]
            });
            allColors.push(lighterColor);
            targetDashArray.push(3);

            // Annotate where estimate first crosses the target date line
            // Solve: lastY + slope*(t - lastT) = targetT  =>  t = lastT + (targetT - lastY) / slope
            if (targetT != null && slope !== 0 && !actualCrossing) {
                const lastT = lastDataPoint.x.getTime();
                const lastY = lastDataPoint.y;
                const tCross = lastT + (targetT - lastY) / slope;
                const maxT = new Date(lastDate.getFullYear() + numberOfEstimateYears, lastDate.getMonth(), 1).getTime();
                if (tCross > lastT && tCross <= maxT) {
                    crossingAnnotations.push({
                        x: tCross,
                        y: targetT,
                        marker: { size: 4, fillColor: lighterColor, strokeColor: targetColors[index] },
                        label: {
                            text: `${countryDisplay}/${categoryDisplay} ~${displayDate(new Date(tCross), true)}`,
                            textAnchor: 'start',
                            offsetX: 4,
                            offsetY: -4,
                            style: { color: targetColors[index], background: 'white', border: 0, fontSize: '11px' },
                        },
                    });
                }
            }
        }
    });

    // Stagger labels vertically when annotations land close together on the x-axis
    crossingAnnotations.sort((a, b) => (a.x as number) - (b.x as number));
    const CLOSE_MS = 365 * 24 * 60 * 60 * 1000;
    let prevX = -Infinity;
    let staggerLevel = 0;
    for (const ann of crossingAnnotations) {
        if ((ann.x as number) - prevX < CLOSE_MS) {
            staggerLevel++;
        } else {
            staggerLevel = 0;
        }
        ann.label.offsetY = -(4 + staggerLevel * 18);
        prevX = ann.x as number;
    }

    if (targetDate) {
        series.push({
            name: 'Target Date',
            data: [
                { x: targetDate, y: targetDate.getTime() },
                { x: referenceEndDate, y: targetDate.getTime() },
            ],
        });
        allColors.push('#999999');
        targetDashArray.push(4);
    }

    // Fix the y-axis range across BOTH date types so the axis doesn't jump when
    // the user toggles between Filing and Final Action dates (Final Action dates
    // are more backlogged, so they span a different, older range).
    const collectYValues = (dt: DateType): number[] => {
        const ys = [minDate.getTime(), referenceEndDate.getTime()];
        if (targetDate) ys.push(targetDate.getTime());
        for (const entry of chartList) {
            const {currData, estimate} = buildEntryData(entry, dt, showEstimate, estimatePeriod);
            for (const pt of currData) ys.push(pt.y);
            if (estimate) for (const pt of estimate.predictions) ys.push(pt.y);
        }
        return ys;
    };
    const combinedYValues = [
        ...collectYValues(DateType.FinalActionDate),
        ...collectYValues(DateType.FilingDate),
    ];
    const yMin = Math.min(...combinedYValues);
    const yMax = Math.max(...combinedYValues);

    const options = {
        stroke: {
            width: 2,
            curve: "straight",
            dashArray: targetDashArray,
        },
        markers: { size: 0},
        xaxis: {
            type: 'datetime',
            // Reapply any retained zoom window so toggling date type keeps the view.
            ...(zoomRange ? {min: zoomRange.min, max: zoomRange.max} : {}),
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
            min: yMin,
            max: yMax,
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
            },
            events: {
                zoomed: (_chartContext, {xaxis}) => {
                    if (xaxis && typeof xaxis.min === 'number' && typeof xaxis.max === 'number') {
                        onZoomChange({min: xaxis.min, max: xaxis.max});
                    } else {
                        // Reset zoom clears min/max; drop the retained window.
                        onZoomChange(null);
                    }
                },
                scrolled: (_chartContext, {xaxis}) => {
                    if (xaxis && typeof xaxis.min === 'number' && typeof xaxis.max === 'number') {
                        onZoomChange({min: xaxis.min, max: xaxis.max});
                    }
                },
                beforeResetZoom: () => {
                    onZoomChange(null);
                },
            },
        },
        grid: {
            position: 'front',
        },
        annotations: {
            points: [
                ...(targetDate ? [{
                    x: targetDate.getTime(),
                    y: targetDate.getTime(),
                    marker: { size: 0 },
                    label: {
                        text: 'Target: ' + displayDate(targetDate, true),
                        textAnchor: 'end',
                        offsetX: -10,
                        offsetY: -2,
                        style: { color: '#666666', background: 'white', border: 0, fontSize: '11px' },
                    },
                }] : []),
                ...crossingAnnotations,
            ],
        },
    };


    return (
        <div className="line">
            <ApexChart options={options} series={series} type="line" width="900px" />
        </div>
    );
}

function Chart({data}: { data: MonthData[] }) {
    const persisted = useMemo(loadState, []);

    const [country, setCountry] = useState<string>("");
    const [category, setCategory] = useState<string>("");

    const [dateType, setDateType] = useState<DateType>(persisted.dateType);

    const [showEstimate, setShowEstimate] = useState<boolean>(persisted.showEstimate);
    const [estimatePeriod, setEstimatePeriod] = useState<number>(persisted.estimatePeriod);

    const [targetDateStr, setTargetDateStr] = useState<string>(persisted.targetDateStr);

    const handleDateTypeChange = (event: ChangeEvent<HTMLInputElement>) => {
        setDateType(parseInt(event.target.value) as DateType);
    };

    const handleEstimateChange = (event: ChangeEvent<HTMLInputElement>) => {
        setShowEstimate(event.target.checked);
    };

    const handleEstimatePeriodChange = (event: ChangeEvent<HTMLInputElement>) => {
        setEstimatePeriod(parseInt(event.target.value));
    };

    const handleTargetDateChange = (event: ChangeEvent<HTMLInputElement>) => {
        setTargetDateStr(event.target.value);
    };

    const handleCountryChange = (event: ChangeEvent<HTMLInputElement>) => {
        setCountry(event.target.value as string);
    };
    const handleCategoryChange = (event: ChangeEvent<HTMLInputElement>) => {
        setCategory(event.target.value as string);
    };

    const [chartList, setChartList] = useState<ChartEntry[]>(persisted.chartList);

    useEffect(() => {
        if (typeof window === "undefined") return;
        try {
            window.localStorage.setItem(STORAGE_KEY, JSON.stringify({
                chartList, dateType, showEstimate, estimatePeriod, targetDateStr,
            }));
        } catch (e) {
            // e.g. private mode / storage full.
            console.warn("Failed to persist chart state:", e);
        }
    }, [chartList, dateType, showEstimate, estimatePeriod, targetDateStr]);
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

    const removeFromChart = (target: ChartEntry) => {
        setChartList((x: ChartEntry[]) => x.filter(
            (entry) => !((entry.country.toLowerCase() === target.country.toLowerCase()) &&
                         (entry.category.toLowerCase() === target.category.toLowerCase()))));
    }

    const targetDate = useMemo(() => {
        if (!targetDateStr) return null;
        const d = new Date(targetDateStr);
        return isNaN(d.getTime()) ? null : d;
    }, [targetDateStr]);

    // Retain the current zoom window across re-renders (e.g. date type toggle).
    // Held in a ref so capturing a zoom doesn't re-render and fight the user;
    // it's read when the chart is rebuilt for another reason.
    const zoomRangeRef = useRef<ZoomRange | null>(null);
    const handleZoomChange = useCallback((range: ZoomRange | null) => {
        zoomRangeRef.current = range;
    }, []);

    const chartDisplay = useMemo(
        () => createChartData(chartList, MinDate, MaxDate, dateType,
                            showEstimate, estimatePeriod, targetDate,
                            zoomRangeRef.current, handleZoomChange),
        [chartList, MinDate, MaxDate, dateType, showEstimate, estimatePeriod, targetDate, handleZoomChange]
    );

    const resetChart = () => {
        // If already empty, restore the default combinations instead of clearing.
        setChartList((x) => x.length === 0 ? [...defaultState.chartList] : []);
        setTargetDateStr("");
        zoomRangeRef.current = null;
    }
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
                <Button onClick={() => resetChart()}
                        variant="contained"
                        color="error">
                    Reset Chart
                </Button>
            </Grid>
        </Grid>
        {chartList.length > 0 && (
            <Box sx={{
                display: 'flex',
                flexWrap: 'wrap',
                justifyContent: 'center',
                gap: 1,
                mt: 2,
            }}>
                {chartList.map((entry) => {
                    const countryDisplay = AllCountries.find(
                        c => c.toLowerCase() === entry.country.toLowerCase()) ?? entry.country;
                    const categoryDisplay = AllVisaTypes.find(
                        c => c.toLowerCase() === entry.category.toLowerCase()) ?? entry.category;
                    return (
                        <Chip
                            key={`${entry.country}/${entry.category}`}
                            label={`${countryDisplay}/${categoryDisplay}`}
                            onDelete={() => removeFromChart(entry)}
                            sx={{
                                '& .MuiChip-deleteIcon': {
                                    color: '#c47b7b',
                                    '&:hover': {
                                        color: 'error.main',
                                    },
                                },
                            }}
                        />
                    );
                })}
            </Box>
        )}
        <Grid container spacing={2} columns={24}
              alignItems="center"
              justifyContent="center"
              sx={{mt: 2}}
        >
            <Grid size={10}>
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
            <Grid size={4}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <TextField
                        type="date"
                        label="Target Date"
                        value={targetDateStr}
                        onChange={handleTargetDateChange}
                        variant="standard"
                        size="small"
                        InputLabelProps={{ shrink: true }}
                    />
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
