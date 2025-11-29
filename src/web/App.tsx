import {useState} from "react";
import Box from '@mui/material/Box';
import Chart from "./chart";
import Table from "./table";
import {Data} from "./all_data";
import AppBar from '@mui/material/AppBar';
import Toolbar from '@mui/material/Toolbar';
import Typography from '@mui/material/Typography';
import Link from '@mui/material/Link';
import Tabs from '@mui/material/Tabs';
import Tab from '@mui/material/Tab';
import GitHubIcon from '@mui/icons-material/GitHub';


const chartData = <Chart data = {Data}></Chart>;
const tableData = <Table data = {Data}></Table>;

function App() {
    const [selectedTab, setSelectedTab] = useState(0);

    const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
        setSelectedTab(newValue);
    };

    return (
        <Box sx={{
            flexGrow: 1,
            background: 'linear-gradient(145deg, #f0f4ff 0%, #ffffff 100%)',
            minHeight: '100vh',
            mt: 0,
            borderRadius: 2
        }}>
            <AppBar position="static" sx={{
                borderRadius: 2,
                bgcolor: 'rgba(255, 255, 255, 0.7)',
                backdropFilter: 'blur(8px)',
                boxShadow: '0 4px 30px rgba(0, 0, 0, 0.1)',
                color: '#1976d2'
            }}>
            <Toolbar>
                <Typography variant="h6" component="div" sx={{flexGrow: 1, color: 'green'}}>
                US Green Card Waiting Time
                    </Typography>
                    <Link href="https://github.com/itsapinhulk/visa-tracker" color="inherit"
                          sx={{
                              mr: 2,
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              borderRadius: '8px',
                              p: 0.5,
                              width: '32px',
                              height: '32px',
                              '&:hover': {
                                  bgcolor: 'rgba(0, 0, 0, 0.1)',
                              }
                          }}>
                        <GitHubIcon sx={{fontSize: '32px', color: 'black'}} />
                    </Link>
                    <Link href="https://itsapinhulk.github.io" color="inherit"
                          sx={{
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              borderRadius: '8px',
                              p: 0.5,
                              width: '32px',
                              height: '32px',
                              '&:hover': {
                                  bgcolor: 'rgba(0, 0, 0, 0.1)',
                              }
                          }}>
                        <img
                            src="https://www.gravatar.com/avatar/005638b36f6a30900c959ef6091c33337fbcc63f735aa76c86b27fdade7bf510?s=80"
                            alt="Profile"
                            style={{
                                width: '32px',
                                height: '32px',
                                borderRadius: '50%'
                            }}
                        />
                    </Link>
                </Toolbar>
            </AppBar>
            <Box sx={{width: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', px: 2}}>
                <Box sx={{
                    borderBottom: 1,
                    borderColor: 'rgba(25, 118, 210, 0.2)',
                    width: '100%',
                    maxWidth: 1200,
                    px: 2,
                    bgcolor: 'rgba(255, 255, 255, 0.5)',
                    borderRadius: '8px 8px 0 0'
                }}>
                <Tabs value={selectedTab} onChange={handleTabChange} centered>
                        <Tab label="Chart" />
                        <Tab label="Table" />
                    </Tabs>
                </Box>
                <Box sx={{p: 3, width: '100%', maxWidth: 1200}}>
                    {selectedTab === 0 ? chartData : tableData}
                </Box>
            </Box>
            <Box sx={{width: '100%', display: 'flex', justifyContent: 'center', pb: 2}}>
                <Typography variant="body2" color="text.secondary">
                    Data source: <Link
                    href="https://travel.state.gov/content/travel/en/legal/visa-law0/visa-bulletin.html" target="_blank"
                    rel="noopener">
                    U.S. Department of State Visa Bulletin
                </Link>
                </Typography>
            </Box>
        </Box>
    );
}

export default App;
