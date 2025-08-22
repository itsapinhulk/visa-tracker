import {AllCountries, AllVisaTypes, MonthData, displayDate} from './all_data';
import { useMemo } from 'react';
import {
    MaterialReactTable,
    useMaterialReactTable,
    type MRT_ColumnDef,
} from 'material-react-table';

function Table({data}: { data: MonthData[] }) {
    const columns = useMemo<MRT_ColumnDef<MonthData>[]>(
        () => [
            {
                header: 'Date',
                accessorKey: 'date',
                id: 'date',
                Cell: ({cell}) => displayDate(cell.getValue(), false),
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
                Cell: ({cell}) => displayDate(cell.getValue(), true),
                size: 120,
                enableColumnFilter : false,
            },
            {
                header: 'Final Action Date',
                accessorKey: 'final_action_date',
                id: 'final_action_date',
                Cell: ({cell}) => displayDate(cell.getValue(), true),
                size: 120,
                enableColumnFilter : false,
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
