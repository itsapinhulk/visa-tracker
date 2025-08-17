import {AllCountries, AllVisaTypes, MonthData} from './all_data';
import { useMemo } from 'react';
import {
    MaterialReactTable,
    useMaterialReactTable,
    type MRT_ColumnDef,
} from 'material-react-table';

function Table({data}: { data: MonthData[] }) {

    const displayDate = (cell, withDay : boolean) => {
        const value = cell.getValue();
        if (value === null) {
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

    // date
    // category
    // country
    // filing_date
    // final_action_date

    const columns = useMemo<MRT_ColumnDef<MonthData>[]>(
        () => [
            {
                header: 'Date',
                accessorKey: 'date',
                id: 'date',
                Cell: ({cell}) => displayDate(cell, false),
                size: 100,
            },
            {
                header: 'Category',
                accessorKey: 'category',
                id: 'category',
                filterVariant: 'select',
                filterSelectOptions: AllVisaTypes,
                size: 80,
            },
            {
                header: 'Country',
                accessorKey: 'country',
                id: 'country',
                filterVariant: 'select',
                filterSelectOptions: AllCountries,
                size: 150,
            },
            {
                header: 'Filing Date',
                accessorKey: 'filing_date',
                id: 'filing_date',
                Cell: ({cell}) => displayDate(cell, true),
                size: 120,
            },
            {
                header: 'Final Action Date',
                accessorKey: 'final_action_date',
                id: 'final_action_date',
                Cell: ({cell}) => displayDate(cell, true),
                size: 120,
            },
       ], [],
    );

    const table = useMaterialReactTable({
        columns,
        data,
        initialState: { showColumnFilters: true },
    });

    return <MaterialReactTable table={table} />;
}

export default Table;
