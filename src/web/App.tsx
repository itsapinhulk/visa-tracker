import {useCallback, useState} from "react";
import Box from '@mui/material/Box';
import Grid from '@mui/material/Grid';
import Stack from '@mui/material/Stack';
import Button from '@mui/material/Button';
import Chart from "./chart";
import Table from "./table";
import {Data, AllVisaTypes, AllCountries} from "./all_data";

enum PageType {
    Chart, Table,
}

const chartData = <Chart data = {Data}></Chart>;
const tableData = <Table data = {Data}></Table>;

function App() {
    const [pageType, setPageType] = useState<PageType>(PageType.Table);

    const buttonType = useCallback((target: PageType) => {
        if (target === pageType) {
            return "contained";
        } else {
            return "outlined";
        }
    }, [pageType]);

    const createButton = useCallback((target: PageType) => {
        let buttonName = "Unhandled";
        let showMsg = "Unhandled";
        if (target === pageType) {
            showMsg = "Showing ";
        } else {
            showMsg = "Show ";
        }
        if (target === PageType.Chart) {
            buttonName = "Chart";
        } else if (target == PageType.Table) {
            buttonName = "Table";
        }
        return (
        <Button onClick = {() => setPageType(target)}
            variant={buttonType(target)}>
            {showMsg} {buttonName}
        </Button>
        );
    }, [pageType]);

    let output = <div>"Unhandled"</div>;
    if (pageType === PageType.Chart) {
        output = chartData;
    } else if (pageType === PageType.Table) {
        output = tableData;
    }

    return (<div>
        <Grid container spacing={2} columns={1}>
           <Grid size={8}>
                <Stack spacing={2} direction="row">
                    {createButton(PageType.Chart)}
                    {createButton(PageType.Table)}
                </Stack>
           </Grid>
           <Grid size={8}>
               <Box>{output}</Box>
           </Grid>
        </Grid>
    </div>
);
}

export default App;
