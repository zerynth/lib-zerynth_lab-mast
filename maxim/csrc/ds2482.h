#ifndef __DS2482_H__
#define __DS2482_H__
    

#define   STATUS_KO     0x00
#define   STATUS_1WB   	0x01   // 1Wire busy
#define   STATUS_PPD   	0x02   // 1Wire pulse detect
#define   STATUS_SD   	0x04   // 1Wire short detect
#define   STATUS_SBR   	0x20    // 1Wire Single Bit Result
#define   STATUS_TSB   	0x40    // 1Wire Triplet Second Bit
#define   STATUS_DIR   	0x80    // 1Wire Branch Direction Taken
#define   POLL_LIMIT   	500      // 5 seconds busy wait

    
// Commands
#define   CMD_DRST   	0xF0  // Device Reset
#define   CMD_WCFG   	0xD2  // Write Config
#define   CMD_SRP   	0xE1  // Set Read Pointer
#define   CMD_CHSL   	0xC3  // Channel select (only 2482-800)
#define   CMD_1WRS   	0xB4  // 1W Reset
#define   CMD_1WWB   	0xA5  // 1W Write Byte
#define   CMD_1WRB   	0x96  // 1W Read Byte
#define   CMD_1WT   	0x78  // 1W Triplet

    
// 1 Wire Primitives
    
int OWReset(void);
int OWWriteByte(unsigned char);
unsigned char OWReadByte(void);
int OWFirst(void);
int OWNext(void);
int OWSearch(void);

#endif
