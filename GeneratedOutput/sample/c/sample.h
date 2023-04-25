#ifndef GENERATED_ASN1SCC_sample_H
#define GENERATED_ASN1SCC_sample_H
/*
Code automatically generated by asn1scc tool
*/
#include "asn1crt.h"

#ifdef  __cplusplus
extern "C" {
#endif


/*-- Message --------------------------------------------*/
typedef struct {
    
    byte arr[10];
} Message_szDescription;

typedef struct {
    asn1SccSint msgId;
    asn1SccSint myflag;
    asn1Real value;
    Message_szDescription szDescription;
    flag isReady;

} Message;

#define ERR_MESSAGE_SZDESCRIPTION		16  /*(SIZE(10))*/
flag Message_szDescription_IsConstraintValid(const Message_szDescription* pVal, int* pErrCode);

#define ERR_MESSAGE		26  /**/
#define ERR_MESSAGE_MSGID		1  /**/
#define ERR_MESSAGE_MYFLAG		6  /**/
#define ERR_MESSAGE_VALUE		11  /**/
#define ERR_MESSAGE_ISREADY		21  /**/
flag Message_IsConstraintValid(const Message* pVal, int* pErrCode);

void Message_szDescription_Initialize(Message_szDescription* pVal);
void Message_Initialize(Message* pVal);

 

/* ================= Encoding/Decoding function prototypes =================
 * These functions are placed at the end of the file to make sure all types
 * have been declared first, in case of parameterized ACN encodings
 * ========================================================================= */

 


#ifdef  __cplusplus
}

#endif

#endif