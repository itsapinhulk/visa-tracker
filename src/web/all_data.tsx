// Read in all the CSV files.
const all_csv_files = import.meta.glob("../../data/*/*.csv",{
    eager: true,
});

export interface MonthData {
    date: Date;
    category: string;
    country: string;
    filing_date: Date | null;
    final_action_date: Date | null;
}

let tempData : MonthData[] = [];
let id = 1;

function convertToDate(dateStr: string) {
    // Need to ensure it is in Eastern Standard Time. The exact time doesn't matter.
    const rawDate = new Date(dateStr);
    return new Date(rawDate.getTime() + 400 * 60000);
}

export function displayDate(value: Date | unknown, withDay : boolean) {
    if (!value) {
        return ""
    }
    const year = value.getFullYear();
    const month = value.toLocaleString('default', {month: 'short'});
    const day = value.toLocaleString('default', {day: '2-digit'});
    if (withDay) {
        return `${year} ${month} ${day}`;
    } else {
        return `${year} ${month}`;
    }
};

// Convert all CSV files into a single data structure.
// Hopefully, all this is being done during the packing process.
for (const path in all_csv_files) {
    const csvData = all_csv_files[path];
    for (const row of csvData.default) {
        const curr_date = new Date(parseInt(row.year), parseInt(row.month) - 1, 1, 12, 0, 0, 0);
        const new_data = {
            id: id,
            date: curr_date,
            category: row.category,
            country: row.country,
            filing_date: row.filing_date ? convertToDate(row.filing_date) : null,
            final_action_date: row.final_action_date ? convertToDate(row.final_action_date) : null,
        } as MonthData;

        tempData.push(new_data);
        id += 1;
    }
}

const Data = [... tempData];
const AllCountries = [... new Set(Data.map(x => x.country))];
const AllVisaTypes = [... new Set(Data.map(x => x.category))];
let tempMinDate = null;
let tempMaxDate = null;
Data.forEach((entry) => {
   if (tempMinDate === null || entry.date < tempMinDate) {
       tempMinDate = entry.date;
   }
   if (tempMaxDate === null || entry.date > tempMaxDate) {
       tempMaxDate = entry.date;
   }
})

const MinDate = tempMinDate;
const MaxDate = tempMaxDate;

export {Data, AllCountries, AllVisaTypes, MinDate, MaxDate};
