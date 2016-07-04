//#define ZERYNTH_PRINTF
#include "zerynth.h"
#include "ds2482.h"

int DS2482_init(unsigned char);
int DS2482_reset(void);
static int32_t DS2482_write(unsigned char cmd, unsigned char args, unsigned char arg);
static unsigned char DS2482_read(unsigned char reg);
static unsigned char DS2482_busy_wait(void);

static uint8_t ds2482_i2c;
static uint8_t ds2482_addr;

//Low level I2C utility functions
static int32_t DS2482_transmit(unsigned char cmd, unsigned char txlen, unsigned char *txb, unsigned char rxlen, unsigned char *rxb){
	unsigned char tx[2];
    unsigned char retries;
    int32_t err;

    tx[0] = cmd;
    if (txlen)
	    tx[1] = *txb;
	retries = 5;

    printf("transmit %x\n",cmd);
    while(retries>0){
        retries--;
        vhalI2CSetAddr(ds2482_i2c,ds2482_addr);
        err = vhalI2CTransmit(ds2482_i2c,tx,1+txlen,rxb,rxlen,TIME_U(500,MILLIS));
        if (err==VHAL_TIMEOUT_ERROR)
            continue;
        else if (err==VHAL_HARDWARE_STATUS_ERROR)
            continue;
        else break;
    }

    printf("err %i\n",err);
	return err;
}




//--------------------------------------------------------------------------
// Select the 1-Wire channel on a DS2482-800.
//
// Returns: TRUE if channel selected
//          FALSE device not detected or failure to perform select
//
int DS2482_channel_select(int channel){
   unsigned char ch, ch_read, check=0xff;

   DS2482_reset();
   // Channel Select (Case A)
   //   S AD,0 [A] CHSL [A] CC [A] Sr AD,1 [A] [RR] A\ P
   //  [] indicates from slave
   //  CC channel value
   //  RR channel read back
   switch (channel)
   {
      default: case 0: ch = 0xF0; ch_read = 0xB8; break;
      case 1: ch = 0xE1; ch_read = 0xB1; break;
      case 2: ch = 0xD2; ch_read = 0xAA; break;
      case 3: ch = 0xC3; ch_read = 0xA3; break;
      case 4: ch = 0xB4; ch_read = 0x9C; break;
      case 5: ch = 0xA5; ch_read = 0x95; break;
      case 6: ch = 0x96; ch_read = 0x8E; break;
      case 7: ch = 0x87; ch_read = 0x87; break;
   };

   DS2482_transmit(CMD_CHSL,1,&ch,1,&check);
   printf("Select %i %x %x\n",channel,ch,check);
    // check for failure due to incorrect read back of channel
    if (check == ch_read) {
        return 1;
    }
    return 0;

}

//Taken from: https://www.maximintegrated.com/en/app-notes/index.mvp/id/3684

//--------------------------------------------------------------------------
// Perform a device reset on the DS2482
//
// Returns: TRUE if device was reset
//          FALSE device not detected or failure to perform reset
//
int DS2482_reset(){
   unsigned char status;

   // Device Reset
   //   S AD,0 [A] DRST [A] Sr AD,1 [A] [SS] A\ P
   //  [] indicates from slave
   //  SS status byte to read to verify state

   DS2482_transmit(CMD_DRST,0,NULL,1,&status);
   printf("reset %x\n",status);
    
   // check for failure due to incorrect read back of status
   return ((status & 0xF7) == 0x10);
}


// wait for 1W operation completion
unsigned char DS2482_poll_completion(void) {
	int count = 0;
    unsigned char reg = 0xF0; //status register
	unsigned char status;

	// loop checking for 1WB bit for completion of 1-Wire operation
    do {
        vosThSleep(TIME_U(10,MILLIS));
		DS2482_transmit(CMD_SRP,1,&reg,1,&status);
        count += 1;
    } while ((status & STATUS_1WB) && count < POLL_LIMIT);

    if ((count<=POLL_LIMIT) && !(status & STATUS_1WB)){
        return status;
    }
    return 0xff;
}



//One Wire Primitives

//--------------------------------------------------------------------------
// Reset all of the devices on the 1-Wire Net and return the result.
//
// Returns: TRUE(1):  presence pulse(s) detected, device(s) reset
//          FALSE(0): no presence pulses detected
//
int OWReset(void){
   unsigned char status;

   // 1-Wire reset (Case B)
   //   S AD,0 [A] 1WRS [A] Sr AD,1 [A] [Status] A [Status] A\ P
   //                                   \--------/
   //                       Repeat until 1WB bit has changed to 0
   //  [] indicates from slave

   DS2482_transmit(CMD_1WRS,0,NULL,0,NULL);

   
   status=DS2482_poll_completion();
   printf("OWRESET status %x\n",status);
   // check for failure due to poll limit reached
   if (status==0xff){
      DS2482_reset();
      return 0;
   }

   // check for presence detect
   if (status & STATUS_PPD)
      return 1;
   else
      return 0;
}
    
//--------------------------------------------------------------------------
// Send 8 bits of communication to the 1-Wire Net and verify that the
// 8 bits read from the 1-Wire Net are the same (write operation).
// The parameter 'sendbyte' least significant 8 bits are used.
//
// 'sendbyte' - 8 bits to send (least significant byte)
//
// Returns:  TRUE: bytes written and echo was the same
//           FALSE: echo was not the same
//
int OWWriteByte(unsigned char sendbyte){
   unsigned char status;

   // 1-Wire Write Byte (Case B)
   //   S AD,0 [A] 1WWB [A] DD [A] Sr AD,1 [A] [Status] A [Status] A\ P
   //                                          \--------/
   //                             Repeat until 1WB bit has changed to 0
   //  [] indicates from slave
   //  DD data to write

   printf("OWWB %x\n",sendbyte);
   
   DS2482_transmit(CMD_1WWB,1,&sendbyte,0,NULL);

   status=DS2482_poll_completion();
   // check for failure due to poll limit reached
   if (status==0xff){
      DS2482_reset();
      return 0;
   }
   return 1;
}
    
//--------------------------------------------------------------------------
// Send 8 bits of read communication to the 1-Wire Net and return the
// result 8 bits read from the 1-Wire Net.
//
// Returns:  8 bits read from 1-Wire Net
//
unsigned char OWReadByte(void){
   unsigned char data, status, reg;

   // 1-Wire Read Bytes (Case C)
   //   S AD,0 [A] 1WRB [A] Sr AD,1 [A] [Status] A [Status] A\
   //                                   \--------/
   //                     Repeat until 1WB bit has changed to 0
   //   Sr AD,0 [A] SRP [A] E1 [A] Sr AD,1 [A] DD A\ P
   //
   //  [] indicates from slave
   //  DD data read

   printf("OWRB\n");
   DS2482_transmit(CMD_1WRB,0,NULL,0,NULL);

   status=DS2482_poll_completion();
   // check for failure due to poll limit reached
   if (status==0xff){
      DS2482_reset();
      return 0;
   }

   reg = 0xE1; //read data register
   DS2482_transmit(CMD_SRP,1,&reg,1,&data);

   return data;
}
    
    
//--------------------------------------------------------------------------
// Use the DS2482 help command '1-Wire triplet' to perform one bit of a
//1-Wire search.
//This command does two read bits and one write bit. The write bit
// is either the default direction (all device have same bit) or in case of
// a discrepancy, the 'search_direction' parameter is used.
//
// Returns The DS2482 status byte result from the triplet command
//
unsigned char DS2482_search_triplet(int search_direction)
{
   unsigned char status,reg;

   // 1-Wire Triplet (Case B)
   //   S AD,0 [A] 1WT [A] SS [A] Sr AD,1 [A] [Status] A [Status] A\ P
   //                                         \--------/
   //                           Repeat until 1WB bit has changed to 0
   //  [] indicates from slave
   //  SS indicates byte containing search direction bit value in msbit

   printf("search_triplet\n");
   reg = search_direction ? 0x80 : 0x00;
   DS2482_transmit(CMD_1WT,1,&reg,0,NULL);

   status = DS2482_poll_completion();
   // check for failure due to poll limit reached
   if (status==0xff){
      DS2482_reset();
      return 0;
   }

   // return status byte
   return status;
}
    
// Search state
unsigned char ROM_NO[8];
int LastDiscrepancy;
int LastFamilyDiscrepancy;
int LastDeviceFlag;
unsigned char crc8;

//--------------------------------------------------------------------------
// Calculate the CRC8 of the byte value provided with the current 
// global 'crc8' value. 
// Returns current global crc8 value
//

static unsigned char calc_crc8(unsigned char data){
	int i; 

	crc8 = crc8 ^ data;
	for (i = 0; i < 8; ++i)
	{
		if (crc8 & 1)
			crc8 = (crc8 >> 1) ^ 0x8c;
		else
			crc8 = (crc8 >> 1);
	}

	return crc8;
}
    
//--------------------------------------------------------------------------
// Find the 'first' devices on the 1-Wire network
// Return TRUE  : device found, ROM number in ROM_NO buffer
//        FALSE : no device present
//
int OWFirst()
{
   // reset the search state
   LastDiscrepancy = 0;
   LastDeviceFlag = 0;
   LastFamilyDiscrepancy = 0;

   return OWSearch();
}

//--------------------------------------------------------------------------
// Find the 'next' devices on the 1-Wire network
// Return TRUE  : device found, ROM number in ROM_NO buffer
//        FALSE : device not found, end of search
//
int OWNext()
{
   // leave the search state alone
   return OWSearch();
}

//--------------------------------------------------------------------------
// The 'OWSearch' function does a general search. This function
// continues from the previous search state. The search state
// can be reset by using the 'OWFirst' function.
// This function contains one parameter 'alarm_only'.
// When 'alarm_only' is TRUE (1) the find alarm command
// 0xEC is sent instead of the normal search command 0xF0.
// Using the find alarm command 0xEC will limit the search to only
// 1-Wire devices that are in an 'alarm' state.
//
// Returns:   TRUE (1) : when a 1-Wire device was found and its
//                       Serial Number placed in the global ROM
//            FALSE (0): when no new device was found.  Either the
//                       last search was the last device or there
//                       are no devices on the 1-Wire Net.
//
int OWSearch()
{
   int id_bit_number;
   int last_zero, rom_byte_number, search_result;
   int id_bit, cmp_id_bit;
   unsigned char rom_byte_mask, search_direction, status;

   // initialize for search
   id_bit_number = 1;
   last_zero = 0;
   rom_byte_number = 0;
   rom_byte_mask = 1;
   search_result = 0;
   crc8 = 0;

   // if the last call was not the last one
   if (!LastDeviceFlag)
   {
      // 1-Wire reset
      if (!OWReset())
      {
         // reset the search
         LastDiscrepancy = 0;
         LastDeviceFlag = 0;
         LastFamilyDiscrepancy = 0;
         return 0;
      }

      // issue the search command
      OWWriteByte(0xF0);

      // loop to do the search
      do
      {
         // if this discrepancy if before the Last Discrepancy
         // on a previous next then pick the same as last time
         if (id_bit_number < LastDiscrepancy)
         {
            if ((ROM_NO[rom_byte_number] & rom_byte_mask) > 0)
               search_direction = 1;
            else
               search_direction = 0;
         }
         else
         {
            // if equal to last pick 1, if not then pick 0
            if (id_bit_number == LastDiscrepancy)
               search_direction = 1;
            else
               search_direction = 0;
         }

         // Perform a triple operation on the DS2482 which will perform
         // 2 read bits and 1 write bit
         status = DS2482_search_triplet(search_direction);

         // check bit results in status byte
         id_bit = ((status & STATUS_SBR) == STATUS_SBR);
         cmp_id_bit = ((status & STATUS_TSB) == STATUS_TSB);
         search_direction =
         	((status & STATUS_DIR) == STATUS_DIR) ? (unsigned char)1 : (unsigned char)0;

         // check for no devices on 1-Wire
         if ((id_bit) && (cmp_id_bit))
            break;
         else
         {
            if ((!id_bit) && (!cmp_id_bit) && (search_direction == 0))
            {
               last_zero = id_bit_number;

               // check for Last discrepancy in family
               if (last_zero < 9)
                  LastFamilyDiscrepancy = last_zero;
            }

            // set or clear the bit in the ROM byte rom_byte_number
            // with mask rom_byte_mask
            if (search_direction == 1)
               ROM_NO[rom_byte_number] |= rom_byte_mask;
            else
               ROM_NO[rom_byte_number] &= (unsigned char)~rom_byte_mask;

            // increment the byte counter id_bit_number
            // and shift the mask rom_byte_mask
            id_bit_number++;
            rom_byte_mask <<= 1;

            // if the mask is 0 then go to new SerialNum byte rom_byte_number
            // and reset mask
            if (rom_byte_mask == 0)
            {
               calc_crc8(ROM_NO[rom_byte_number]);  // accumulate the CRC
               rom_byte_number++;
               rom_byte_mask = 1;
            }
         }
      }
      while(rom_byte_number < 8);  // loop until through all ROM bytes 0-7

      // if the search was successful then
      if (!((id_bit_number < 65) || (crc8 != 0)))
      {
         // search successful so set LastDiscrepancy,LastDeviceFlag
         // search_result
         LastDiscrepancy = last_zero;

         // check for last device
         if (LastDiscrepancy == 0)
            LastDeviceFlag = 1;

         search_result = 1;
      }
   }

   // if no device found then reset counters so next
   // 'search' will be like a first

   if (!search_result || (ROM_NO[0] == 0))
   {
      LastDiscrepancy = 0;
      LastDeviceFlag = 0;
      LastFamilyDiscrepancy = 0;
      search_result = 0;
   }

   return search_result;
}


//ZERYNTH INTERFACE
C_NATIVE(_DS2482_init){
    NATIVE_UNWARN();
    int32_t i,err=1;
    CHECK_ARG(args[0],PSMALLINT);
    CHECK_ARG(args[1],PSMALLINT);
    CHECK_ARG(args[2],PSMALLINT);
    ds2482_i2c = PSMALLINT_VALUE(args[0])&0xff;
    ds2482_addr = PSMALLINT_VALUE(args[1])&0xff;
    unsigned char ch = PSMALLINT_VALUE(args[2])&0xff;

    DS2482_reset();
    if(ch!=0) err = DS2482_channel_select(ch);

    if (err)
        err = ERR_OK;
    else err = VHAL_HARDWARE_STATUS_ERROR;
    *res = MAKE_NONE();
    return err;
}

C_NATIVE(_ow_search_all){
    NATIVE_UNWARN();
    PSet *set = pset_new(PSET,0);
    int32_t t=0;

    t = OWFirst();
    while(t){
        printf("searched %i %i %i %i %i %i %i %i %i\n",t,ROM_NO[0],ROM_NO[1],ROM_NO[2],
           ROM_NO[3],ROM_NO[4],ROM_NO[5],ROM_NO[6],ROM_NO[7]);
        PBytes *pbid = pbytes_new(8,ROM_NO);
        pset_put(set,pbid);
        t = OWSearch();
    }

    
    *res= set;
    return ERR_OK;
}

C_NATIVE(_ow_rr){

    int32_t err = OWReset();
    *res = (err) ? PSMALLINT_NEW(1):PSMALLINT_NEW(0);
    return ERR_OK;
}

C_NATIVE(_ow_wb){
    CHECK_ARG(args[0],PSMALLINT);
    int32_t v = PSMALLINT_VALUE(args[0]);
    if(v<0 || v>0xff)
        return ERR_TYPE_EXC;
    int32_t err = OWWriteByte((unsigned char)v);
    if(!err) return VHAL_HARDWARE_STATUS_ERROR;
    *res = MAKE_NONE();
    return ERR_OK;
}

C_NATIVE(_ow_rb){
    int32_t err = OWReadByte();
    *res = PSMALLINT_NEW(err);
    return ERR_OK;
}


C_NATIVE(_ow_get_funcs){
    NATIVE_UNWARN();
    *res = ptuple_new(3,NULL);
    void *owrr = (void*)OWReset;
    void *owrb = (void*)OWReadByte;
    void *owrw = (void*)OWWriteByte;
    PTUPLE_SET_ITEM(*res,0,PSMALLINT_NEW((uint32_t)owrr));
    PTUPLE_SET_ITEM(*res,1,PSMALLINT_NEW((uint32_t)owrb));
    PTUPLE_SET_ITEM(*res,2,PSMALLINT_NEW((uint32_t)owrw));
    return ERR_OK;
}
